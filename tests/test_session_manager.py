"""Tests for SessionManager."""
from unittest.mock import patch
from iribot.session_manager import SessionManager
from iribot.models import MessageRecord, ToolCallRecord


def test_session_manager_basic_flow(tmp_path):
    manager = SessionManager(storage_path=str(tmp_path))
    session = manager.create_session(title="Test")

    user_record = MessageRecord(role="user", content="hello").model_dump()
    manager.add_record(session.id, user_record)

    assistant_record = MessageRecord(role="assistant", content="thinking").model_dump()
    manager.add_record(session.id, assistant_record)

    tool_record = ToolCallRecord(
        tool_call_id="call-1",
        tool_name="shell_run",
        arguments={"cmd": "echo"},
        result={"ok": True},
        success=True,
    ).model_dump()
    manager.add_record(session.id, tool_record)

    messages = manager.get_messages_for_llm(session.id)
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["tool_calls"][0]["function"]["name"] == "shell_run"
    assert messages[-1]["role"] == "tool"

    assert manager.get_session(session.id) is not None
    assert manager.delete_session(session.id) is True
    assert manager.get_session(session.id) is None


def test_migrate_old_format(tmp_path):
    manager = SessionManager(storage_path=str(tmp_path))
    data = {
        "id": "1",
        "title": "Old",
        "messages": [
            {"role": "user", "content": "hi", "timestamp": "t"},
        ],
        "system_prompt": "sys",
        "created_at": "t0",
    }
    migrated = manager._migrate_old_format(data)
    assert "records" in migrated
    assert "messages" not in migrated
    assert migrated["records"][0]["role"] == "system"


def test_delete_missing_session(tmp_path):
    manager = SessionManager(storage_path=str(tmp_path))
    assert manager.delete_session("does-not-exist") is False


def test_update_session_title(tmp_path):
    manager = SessionManager(storage_path=str(tmp_path))
    session = manager.create_session(title="Old Title")
    before_updated_at = session.updated_at

    updated = manager.update_session_title(session.id, "New Title")
    assert updated is not None
    assert updated.title == "New Title"
    assert updated.updated_at >= before_updated_at

    persisted = manager.get_session(session.id)
    assert persisted is not None
    assert persisted.title == "New Title"

    assert manager.update_session_title("does-not-exist", "X") is None


def test_tool_call_truncation(tmp_path):
    """Test that older tool calls are truncated after tool_history_rounds"""
    with patch("iribot.session_manager.settings") as mock_settings:
        mock_settings.tool_history_rounds = 2  # Keep only last 2 tool calls
        
        manager = SessionManager(storage_path=str(tmp_path))
        session = manager.create_session(title="Test Truncation")
        
        # Add 4 tool calls (more than tool_history_rounds)
        for i in range(4):
            # User message
            user_record = MessageRecord(role="user", content=f"Request {i}").model_dump()
            manager.add_record(session.id, user_record)
            
            # Assistant message with tool call
            assistant_record = MessageRecord(role="assistant", content=f"Thinking {i}").model_dump()
            manager.add_record(session.id, assistant_record)
            
            # Tool call
            tool_record = ToolCallRecord(
                tool_call_id=f"call-{i}",
                tool_name=f"tool_{i}",
                arguments={"index": i, "detail": f"detail_{i}"},
                result={"output": f"result_{i}"},
                success=True,
            ).model_dump()
            manager.add_record(session.id, tool_record)
        
        messages = manager.get_messages_for_llm(session.id)
        
        # Find tool calls in messages
        tool_call_messages = [m for m in messages if m.get("role") == "assistant" and "tool_calls" in m]
        tool_result_messages = [m for m in messages if m.get("role") == "tool"]
        
        # We should have 4 assistant messages with tool calls
        assert len(tool_call_messages) == 4
        assert len(tool_result_messages) == 4
        
        # First 2 tool calls should be truncated (only tool name preserved)
        for i in range(2):
            tool_call = tool_call_messages[i]["tool_calls"][0]
            assert tool_call["function"]["name"] == f"tool_{i}"
            assert tool_call["function"]["arguments"] == "{}"  # Arguments truncated
            assert "truncated" in tool_result_messages[i]["content"].lower()  # Result truncated
        
        # Last 2 tool calls should have full details
        for i in range(2, 4):
            tool_call = tool_call_messages[i]["tool_calls"][0]
            assert tool_call["function"]["name"] == f"tool_{i}"
            assert f"detail_{i}" in tool_call["function"]["arguments"]  # Arguments preserved
            assert f"result_{i}" in tool_result_messages[i]["content"]  # Result preserved
