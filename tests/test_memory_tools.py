"""Tests for memory tools."""

from iribot.executor import ToolExecutor
from iribot.session_manager import SessionManager


def test_memory_tools_flow(tmp_path, monkeypatch):
    manager = SessionManager(storage_path=str(tmp_path))
    session = manager.create_session(title="memory-tools")

    import iribot.tools.memory as memory_module

    monkeypatch.setattr(memory_module, "session_manager", manager)

    executor = ToolExecutor()

    remember = executor.execute_tool(
        "memory_remember",
        session_id=session.id,
        content="用户喜欢英文代码注释",
        tags=["preference"],
    )
    assert remember["success"] is True

    memory_id = remember["memory"]["id"]

    listed = executor.execute_tool("memory_list", session_id=session.id)
    assert listed["success"] is True
    assert listed["count"] == 1

    forgotten = executor.execute_tool("memory_forget", session_id=session.id, memory_id=memory_id)
    assert forgotten["success"] is True

    listed_after = executor.execute_tool("memory_list", session_id=session.id)
    assert listed_after["count"] == 0
