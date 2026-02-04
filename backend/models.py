"""Data models for the Agent application"""
from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field


def get_local_now():
    """Get the current local time."""
    return datetime.now()


# ============ Session Record Types ============

class MessageRecord(BaseModel):
    """Message record - represents a message in the conversation"""
    type: Literal["message"] = "message"
    role: Literal["system", "user", "assistant"]
    content: str
    binary_content: Optional[List[Dict[str, Any]]] = None  # Images, files, etc.
    timestamp: datetime = Field(default_factory=get_local_now)


class ToolCallRecord(BaseModel):
    """Tool call record - represents a single tool invocation and result"""
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    timestamp: datetime = Field(default_factory=get_local_now)


# Union type for session records
SessionRecord = Union[MessageRecord, ToolCallRecord]


# ============ Session Model ============

class Session(BaseModel):
    """Session model with unified record list"""
    id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    title: str
    records: List[Dict[str, Any]] = []  # List of MessageRecord or ToolCallRecord
    created_at: datetime = Field(default_factory=get_local_now)
    updated_at: datetime = Field(default_factory=get_local_now)
    system_prompt: str  # Required field, must be provided when creating session


# ============ API Request/Response Models ============

class ChatRequest(BaseModel):
    """Chat request model"""
    session_id: str
    message: str
    binary_content: Optional[List[Dict[str, Any]]] = None

class SystemPromptUpdate(BaseModel):
    """System prompt update model"""
    system_prompt: str


# ============ Prompt Generation Models ============

class SystemPromptGenerateRequest(BaseModel):
    """Request to generate a system prompt"""
    custom_instructions: str = ""


class SystemPromptGenerateResponse(BaseModel):
    """Response containing generated system prompt"""
    system_prompt: str
    datetime_info: dict


class SessionCreate(BaseModel):
    """Create new session request"""
    title: str = "New Chat"
    system_prompt: Optional[str] = None
