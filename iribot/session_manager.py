"""Session management for storing and retrieving chat sessions"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import settings
from .models import Session


class SessionManager:
    """Manages chat sessions and persistence"""

    def __init__(self, storage_path: str = "./sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.sessions: dict[str, Session] = {}
        self._load_all_sessions()

    def create_session(self, title: str = "New Chat") -> Session:
        """Create a new session"""
        session = Session(title=title)
        self.sessions[session.id] = session
        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID"""
        return self.sessions.get(session_id)

    def list_sessions(self) -> list[Session]:
        """List all sessions sorted by updated_at descending"""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )

    def add_record(self, session_id: str, record: dict[str, Any]) -> Session | None:
        """Add a record to a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        session.records.append(record)
        session.updated_at = datetime.now()
        self._save_session(session)
        return session

    def add_records(self, session_id: str, records: list[dict[str, Any]]) -> Session | None:
        """Add multiple records to a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        session.records.extend(records)
        session.updated_at = datetime.now()
        self._save_session(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id not in self.sessions:
            return False

        del self.sessions[session_id]
        session_file = self.storage_path / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
        return True

    def get_messages_for_llm(self, session_id: str) -> list[dict[str, Any]]:
        """Extract messages in LLM-compatible format from session records"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        # First pass: count total tool calls
        total_tool_calls = sum(1 for r in session.records if r.get("type") == "tool_call")
        tool_history_rounds = settings.tool_history_rounds

        # Calculate the threshold: tool calls with index <= threshold should be truncated
        # We keep the most recent `tool_history_rounds` tool calls
        truncation_threshold = total_tool_calls - tool_history_rounds

        messages = []
        tool_call_index = 0
        last_assistant_message = None

        for record in session.records:
            if record.get("type") == "message":
                role = record.get("role")
                content = record.get("content", "")

                if role not in {"system", "user", "assistant"}:
                    raise ValueError(f"Invalid message role: {role}")
                
                reasoning_content = record.get("reasoning_content", None)

                messages.append({"role": role, "content": content, "reasoning_content": reasoning_content})

                if role == "assistant":
                    last_assistant_message = messages[-1]

            elif record.get("type") == "tool_call":
                tool_call_index += 1
                should_truncate = tool_call_index <= truncation_threshold

                tool_call_id = record.get("tool_call_id")
                tool_name = record.get("tool_name")
                arguments = record.get("arguments", {})
                result = record.get("result")

                # Find the corresponding assistant message with matching tool_call
                # The assistant message should already have tool_calls from service.py
                if not last_assistant_message:
                    raise ValueError(f"Tool call record {tool_call_id} does not have a preceding assistant message")

                # Ensure tool_calls list exists (for backward compatibility)
                if "tool_calls" not in last_assistant_message:
                    last_assistant_message["tool_calls"] = []

                if should_truncate:
                    last_assistant_message["tool_calls"].append({
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": "{}"
                        }
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": "[Tool call details truncated]"
                    })
                else:
                    last_assistant_message["tool_calls"].append({
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
                        }
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(result) if isinstance(result, dict) else str(result)
                    })

        return messages

    def _save_session(self, session: Session) -> None:
        """Save session to disk"""
        session_file = self.storage_path / f"{session.id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.model_dump(), f, indent=2, default=str, ensure_ascii=False)

    def _load_all_sessions(self) -> None:
        """Load all sessions from disk"""
        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file, encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error loading session {session_file}: {e}")
                continue
            try:
                if "messages" in data and "records" not in data:
                    data = self._migrate_old_format(data)
                session = Session(**data)
                self.sessions[session.id] = session
            except Exception as e:
                print(f"Error parsing session {session_file}: {e}")

    def _migrate_old_format(self, data: dict) -> dict:
        """Migrate from old message format to new record format"""
        records = []

        # Add system message
        records.append({
            "type": "message",
            "role": "system",
            "content": data.get("system_prompt", ""),
            "timestamp": data.get("created_at")
        })

        # Convert old messages to records
        records.extend({
            "type": "message",
            "role": msg.get("role"),
            "content": msg.get("content", ""),
            "binary_content": msg.get("binary_content"),
            "timestamp": msg.get("timestamp")
        } for msg in data.get("messages", []))

        data["records"] = records
        del data["messages"]
        return data


# Global session manager instance
session_manager = SessionManager()
