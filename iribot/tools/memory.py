"""Memory management tools for storing important session facts."""
from typing import Any

from .base import BaseTool
from ..session_manager import session_manager


class MemoryRememberTool(BaseTool):
    @property
    def name(self) -> str:
        return "memory_remember"

    @property
    def description(self) -> str:
        return "Remember important information for the current session so it can be reused later."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier",
                },
                "content": {
                    "type": "string",
                    "description": "Important fact to remember.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorization.",
                },
            },
            "required": ["session_id", "content"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        session_id = kwargs.get("session_id")
        content = (kwargs.get("content") or "").strip()
        tags = kwargs.get("tags") or []

        if not session_id:
            return {"success": False, "error": "session_id is required"}
        if not content:
            return {"success": False, "error": "content cannot be empty"}

        memory = session_manager.add_memory(session_id=session_id, content=content, tags=tags)
        if memory is None:
            return {"success": False, "error": "session not found"}

        return {"success": True, "memory": memory}


class MemoryListTool(BaseTool):
    @property
    def name(self) -> str:
        return "memory_list"

    @property
    def description(self) -> str:
        return "List all remembered important information for the current session."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier",
                },
            },
            "required": ["session_id"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        session_id = kwargs.get("session_id")
        if not session_id:
            return {"success": False, "error": "session_id is required"}
        memories = session_manager.list_memories(session_id=session_id)
        return {"success": True, "memories": memories, "count": len(memories)}


class MemoryForgetTool(BaseTool):
    @property
    def name(self) -> str:
        return "memory_forget"

    @property
    def description(self) -> str:
        return "Forget a previously stored memory by ID."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier",
                },
                "memory_id": {
                    "type": "string",
                    "description": "ID returned by memory_remember.",
                },
            },
            "required": ["session_id", "memory_id"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        session_id = kwargs.get("session_id")
        memory_id = kwargs.get("memory_id")
        if not session_id or not memory_id:
            return {"success": False, "error": "session_id and memory_id are required"}

        deleted = session_manager.delete_memory(session_id=session_id, memory_id=memory_id)
        if not deleted:
            return {"success": False, "error": "memory not found"}

        return {"success": True, "memory_id": memory_id}
