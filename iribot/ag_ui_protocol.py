"""AG-UI Protocol implementation for chat messages"""
import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class ToolCall:
    """Tool function call"""
    id: str
    type: Literal["function"] = "function"
    function: dict = field(default_factory=lambda: {"name": "", "arguments": ""})

    def to_dict(self):
        return asdict(self)


@dataclass
class BinaryContent:
    """Binary content (image, file, etc.)"""
    type: Literal["binary"] = "binary"
    mime_type: str = "image/jpeg"
    data: str | None = None  # base64 encoded
    id: str | None = None
    url: str | None = None
    filename: str | None = None

    def to_dict(self):
        return asdict(self)


@dataclass
class AGUIMessage:
    """AG-UI Protocol Message"""
    id: str
    role: str  # "user", "assistant", "system", etc.
    content: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    binary_content: list[BinaryContent] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_message(cls, message: dict) -> AGUIMessage:
        """Convert chat message to AG-UI format"""
        msg_id = message.get("id", str(uuid.uuid4()))

        # Convert legacy 'images' field to binary_content
        binary_content = message.get("binary_content") or []
        if not binary_content and message.get("images"):
            # Auto-convert images to binary_content format
            binary_content = [
                BinaryContent(
                    type="binary",
                    mimeType="image/jpeg",
                    data=img,
                    id=f"img_{i}"
                ).to_dict()
                for i, img in enumerate(message.get("images", []))
            ]

        # Ensure metadata includes timestamp
        metadata = message.get("metadata") or {}
        if "timestamp" not in metadata and message.get("timestamp"):
            timestamp = message.get("timestamp")
            if hasattr(timestamp, 'isoformat'):
                metadata["timestamp"] = timestamp.isoformat()
            else:
                metadata["timestamp"] = str(timestamp)

        return cls(
            id=msg_id,
            role=message.get("role", "user"),
            content=message.get("content"),
            name=message.get("name"),
            tool_calls=message.get("tool_calls") or [],
            tool_results=message.get("tool_results") or [],
            binary_content=binary_content,
            metadata=metadata
        )

    def to_dict(self):
        """Convert to AG-UI protocol dict"""
        data = {
            "id": self.id,
            "role": self.role,
        }

        if self.content:
            data["content"] = self.content

        if self.name:
            data["name"] = self.name

        if self.tool_calls:
            data["tool_calls"] = [
                tc.to_dict() if hasattr(tc, 'to_dict') else tc
                for tc in self.tool_calls
            ]

        if self.tool_results:
            data["tool_results"] = self.tool_results

        if self.binary_content:
            data["binary_content"] = [
                bc.to_dict() if hasattr(bc, 'to_dict') else bc
                for bc in self.binary_content
            ]

        if self.metadata:
            data["metadata"] = self.metadata

        return data

    def to_json(self):
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class AGUIEventEncoder:
    """Encodes and decodes AG-UI protocol events"""

    @staticmethod
    def encode_message(message: AGUIMessage) -> str:
        """Encode AG-UI message to JSON"""
        return message.to_json()

    @staticmethod
    def decode_message(data: str) -> AGUIMessage:
        """Decode AG-UI message from JSON"""
        msg_dict = json.loads(data)
        return AGUIMessage(
            id=msg_dict.get("id", str(uuid.uuid4())),
            role=msg_dict.get("role", "user"),
            content=msg_dict.get("content"),
            name=msg_dict.get("name"),
            tool_calls=msg_dict.get("tool_calls", []),
            tool_results=msg_dict.get("tool_results", []),
            binary_content=msg_dict.get("binary_content", []),
            metadata=msg_dict.get("metadata", {})
        )

    @staticmethod
    def event_stream(messages: list[dict]) -> list[str]:
        """Convert messages to AG-UI event stream"""
        events = []
        for msg in messages:
            ag_msg = AGUIMessage.from_message(msg)
            events.append(ag_msg.to_json())
        return events


def convert_to_ag_ui(message: dict) -> dict:
    """Helper function to convert message to AG-UI format"""
    ag_msg = AGUIMessage.from_message(message)
    return ag_msg.to_dict()


def convert_messages_to_ag_ui(messages: list[dict]) -> list[dict]:
    """Convert list of messages to AG-UI format"""
    return [convert_to_ag_ui(msg) for msg in messages]


@dataclass
class ToolCallRecordAGUI:
    """AG-UI format for tool call record"""
    tool_call_id: str
    tool_name: str
    arguments: dict
    result: Any
    success: bool
    timestamp: str | None = None

    def to_dict(self):
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "success": self.success,
            "timestamp": self.timestamp
        }


@dataclass
class LLMCallRecordAGUI:
    """AG-UI format for LLM call record"""
    id: str
    request_messages: list[dict]
    response_content: str | None = None
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[ToolCallRecordAGUI] = field(default_factory=list)
    finish_reason: str | None = None
    timestamp: str | None = None

    def to_dict(self):
        return {
            "id": self.id,
            "request_messages": self.request_messages,
            "response_content": self.response_content,
            "tool_calls": self.tool_calls,
            "tool_results": [
                tr.to_dict() if hasattr(tr, 'to_dict') else tr
                for tr in self.tool_results
            ],
            "finish_reason": self.finish_reason,
            "timestamp": self.timestamp
        }


def convert_llm_calls_to_ag_ui(llm_calls: list[dict]) -> list[dict]:
    """Convert LLM call records to AG-UI format"""
    result = []
    for call in llm_calls:
        tool_results = []
        if call.get("tool_results"):
            for tr in call["tool_results"]:
                timestamp = tr.get("timestamp")
                if hasattr(timestamp, 'isoformat'):
                    timestamp = timestamp.isoformat()
                tool_results.append(ToolCallRecordAGUI(
                    tool_call_id=tr.get("tool_call_id", ""),
                    tool_name=tr.get("tool_name", ""),
                    arguments=tr.get("arguments", {}),
                    result=tr.get("result"),
                    success=tr.get("success", False),
                    timestamp=str(timestamp) if timestamp else None
                ))

        timestamp = call.get("timestamp")
        if hasattr(timestamp, 'isoformat'):
            timestamp = timestamp.isoformat()

        ag_call = LLMCallRecordAGUI(
            id=call.get("id", ""),
            request_messages=call.get("request_messages", []),
            response_content=call.get("response_content"),
            tool_calls=call.get("tool_calls") or [],
            tool_results=tool_results,
            finish_reason=call.get("finish_reason"),
            timestamp=str(timestamp) if timestamp else None
        )
        result.append(ag_call.to_dict())
    return result
