"""Execute command tool with interactive shell sessions"""
import os
import subprocess
import platform
import threading
import time
import uuid
from collections import deque
from typing import Any, Dict, Optional, Deque, Tuple, List
from .base import BaseTool, BaseToolGroup, BaseStatus
from ..config import settings


class ShellSession:
    """Persistent shell session with async output capture"""

    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir
        self._output: Deque[Tuple[str, str]] = deque()
        self._log: Deque[Dict[str, str]] = deque()
        self._output_event = threading.Event()
        self._lock = threading.Lock()
        self._running_marker: Optional[str] = None  # Track if command is running

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Use UTF-8 encoding for both Windows and Unix
        # Git Bash and Python both support UTF-8 well
        encoding = "utf-8"
        
        # Disable colors and set simple terminal to avoid ANSI escape sequences
        env["TERM"] = "dumb"
        env["PS1"] = "$ "  # Simple prompt without colors
        env["NO_COLOR"] = "1"  # Disable colors in many tools
        env["PYTHONUNBUFFERED"] = "1"  # Disable Python output buffering
        
        # Always use bash, get path from config
        bash_cmd = settings.bash_path
        # Use --norc --noprofile to avoid loading user configs that add colors
        # Don't use -i to avoid "no job control" warnings in non-TTY environment
        cmd = [bash_cmd, "--norc", "--noprofile"]

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir if working_dir else None,
            text=True,
            bufsize=1,
            env=env,
            encoding=encoding,
            errors="replace",
        )

        self._stdout_thread = threading.Thread(
            target=self._read_stream,
            args=("stdout", self.process.stdout),
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stream,
            args=("stderr", self.process.stderr),
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stream(self, stream_name: str, stream):
        try:
            for line in iter(stream.readline, ""):
                if line:
                    with self._lock:
                        self._output.append((stream_name, line))
                        self._log.append({"stream": stream_name, "data": line})
                        self._output_event.set()
        except Exception:
            pass
        finally:
            stream.close()

    def is_alive(self) -> bool:
        return self.process and self.process.poll() is None

    def write(self, data: str) -> None:
        if not self.is_alive():
            raise RuntimeError("Shell session is not running")
        if not data.endswith("\n"):
            data += "\n"
        with self._lock:
            self._log.append({"stream": "stdin", "data": data})
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def read(self, wait_ms: int = 0, max_chars: int = 20000) -> Dict[str, Any]:
        output = []
        stderr = []

        if wait_ms > 0:
            self._output_event.wait(wait_ms / 1000)

        with self._lock:
            char_count = 0
            while self._output and char_count <= max_chars:
                stream_name, line = self._output.popleft()
                char_count += len(line)
                if stream_name == "stdout":
                    output.append(line)
                else:
                    stderr.append(line)
            self._output_event.clear()

        return {
            "stdout": "".join(output),
            "stderr": "".join(stderr),
        }

    def terminate(self) -> None:
        if self.is_alive():
            self.process.terminate()

    def get_log(self) -> list:
        with self._lock:
            return list(self._log)
    
    def is_running(self) -> bool:
        """Check if a command is currently running (marker not yet seen)"""
        if self._running_marker is None:
            return False
        
        # Check if marker is already in the buffered output
        # This handles the case where command completed but we didn't wait long enough
        with self._lock:
            new_output = deque()
            marker_found = False
            for stream_name, line in self._output:
                if self._running_marker in line:
                    # Marker found in buffer, command has completed
                    marker_found = True
                    # Remove the marker line from output
                    continue
                new_output.append((stream_name, line))
            
            if marker_found:
                self._output = new_output
                self._running_marker = None
                return False
        
        return True
    
    def set_running_marker(self, marker: str) -> None:
        """Set the marker for currently running command"""
        with self._lock:
            self._running_marker = marker
    
    def clear_running_marker(self) -> None:
        """Clear the running marker when command completes"""
        with self._lock:
            self._running_marker = None


_shell_sessions: Dict[str, ShellSession] = {}


def _collect_output_until_marker(
    session: ShellSession,
    marker: str,
    wait_ms: int,
    max_chars: int,
) -> Tuple[str, str, bool]:
    """
    Collect output from session until marker is found or timeout.
    
    Returns: (stdout, stderr, marker_found)
    """
    max_wait_time = wait_ms if wait_ms > 0 else 100000
    start_time = time.time() * 1000
    all_stdout = []
    all_stderr = []
    marker_found = False

    while (time.time() * 1000 - start_time) < max_wait_time:
        output = session.read(wait_ms=100, max_chars=max_chars)
        stdout_chunk = output.get("stdout", "")
        stderr_chunk = output.get("stderr", "")

        if marker in stdout_chunk:
            # Remove the marker and everything after it (including the marker line)
            lines = stdout_chunk.split('\n')
            filtered_lines = []
            for line in lines:
                if marker in line:
                    marker_found = True
                    break
                filtered_lines.append(line)
            stdout_chunk = '\n'.join(filtered_lines)
            # Add final newline if there were lines
            if filtered_lines and stdout_chunk and not stdout_chunk.endswith('\n'):
                stdout_chunk += '\n'

        if stdout_chunk:
            all_stdout.append(stdout_chunk)
        if stderr_chunk:
            all_stderr.append(stderr_chunk)

        if marker_found:
            # Clear running marker when command completes
            session.clear_running_marker()
            break

        if not stdout_chunk and not stderr_chunk:
            time.sleep(0.01)

    return "".join(all_stdout), "".join(all_stderr), marker_found


def _ensure_session(session_id: str, working_dir: Optional[str] = None) -> ShellSession:
    if session_id not in _shell_sessions or not _shell_sessions[session_id].is_alive():
        _shell_sessions[session_id] = ShellSession(working_dir=working_dir)
        if working_dir:
            _shell_sessions[session_id].write(f'cd "{working_dir}"')
    return _shell_sessions[session_id]


def _get_sessions_status() -> List[Dict[str, Any]]:
    sessions = []
    for session_id, session in _shell_sessions.items():
        sessions.append({
            "session_id": session_id,
            "working_dir": session.working_dir,
            "alive": session.is_alive(),
            "pid": session.process.pid if session.process else None,
            "log": session.get_log(),
        })
    return sessions


class ShellStartTool(BaseTool):
    """Start a persistent shell session"""

    @property
    def name(self) -> str:
        return "shell_start"

    @property
    def description(self) -> str:
        return "Start a persistent bash shell session."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session/agent identifier for persistent shell",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory to start shell (optional)",
                },
            },
            "required": [],
        }

    def execute(
        self,
        session_id: Optional[str] = None,
        working_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or "default"
        _ensure_session(session_id, working_dir=working_dir)
        return {
            "success": True,
            "session_id": session_id,
            "status": "started",
        }


class ShellRunTool(BaseTool):
    """Run a command in a shell session"""

    @property
    def name(self) -> str:
        return "shell_run"

    @property
    def description(self) -> str:
        return "Run a command in a persistent bash session. **IMPORTANT**: If 'background' is set to true, the command will run in the background and the tool will return immediately. This will occupy the shell session; start a new session for other commands."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session/agent identifier for persistent shell",
                },
                "command": {
                    "type": "string",
                    "description": "Command to run",
                },
                "wait_ms": {
                    "type": "integer",
                    "description": "Max wait time in milliseconds for command completion",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return from buffered output",
                    "default": 20000,
                },
                "background": {
                    "type": "boolean",
                    "description": "Run command in background and return immediately. **IMPORTANT** This will occupy the shell session; start a new session for other commands.",
                    "default": False,
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory to start shell (optional)",
                },
            },
            "required": ["command", "background"],
        }

    def execute(
        self,
        command: str,
        session_id: Optional[str] = None,
        wait_ms: Optional[int] = None,
        max_chars: int = 20000,
        background: bool = False,
        working_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or "default"
        session = _ensure_session(session_id, working_dir=working_dir)

        # Check if session is already running a command
        if session.is_running():
            return {
                "success": False,
                "error": f"Session '{session_id}' is already running a command. Please wait for it to complete, use shell_read to check status, or start a new session to run another command.",
                "session_id": session_id,
            }

        if wait_ms is None:
            wait_ms = 10000 if background else 100000

        marker = f"__CMD_DONE_{uuid.uuid4().hex[:8]}__"
        
        # Mark session as running before executing command
        session.set_running_marker(marker)

        session.write(command)
        session.write(f"echo {marker}")

        if background:
            # For background mode, wait for marker with a reasonable timeout
            # If marker is found, command completed and marker will be cleared
            # If marker is not found, command is still running, keep marker set
            # (is_running() will check buffer for marker before rejecting new commands)
            stdout, stderr, marker_found = _collect_output_until_marker(
                session, marker, wait_ms, max_chars
            )
            
            status = "completed" if marker_found else "running"
            
            return {
                "success": True,
                "session_id": session_id,
                "status": status,
                "stdout": stdout,
                "stderr": stderr,
            }
        else:
            # For normal mode, wait until completion or timeout
            max_wait_time = wait_ms if wait_ms > 0 else 100000
            stdout, stderr, marker_found = _collect_output_until_marker(
                session, marker, max_wait_time, max_chars
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "stdout": stdout,
                "stderr": stderr,
            }


class ShellWriteTool(BaseTool):
    """Write input to a shell session"""

    @property
    def name(self) -> str:
        return "shell_write"

    @property
    def description(self) -> str:
        return "Write input to stdin of a persistent bash session."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session/agent identifier for persistent shell",
                },
                "input": {
                    "type": "string",
                    "description": "Input to write to stdin",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory to start shell (optional)",
                },
            },
            "required": ["input"],
        }

    def execute(
        self,
        input: str,
        session_id: Optional[str] = None,
        working_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or "default"
        session = _ensure_session(session_id, working_dir=working_dir)
        session.write(input)
        return {
            "success": True,
            "session_id": session_id,
        }


class ShellReadTool(BaseTool):
    """Read output from a shell session"""

    @property
    def name(self) -> str:
        return "shell_read"

    @property
    def description(self) -> str:
        return "Read buffered output from a persistent bash session."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session/agent identifier for persistent shell",
                },
                "wait_ms": {
                    "type": "integer",
                    "description": "Wait time in milliseconds before reading output",
                    "default": 0,
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return from buffered output",
                    "default": 20000,
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory to start shell (optional)",
                },
            },
            "required": [],
        }

    def execute(
        self,
        session_id: Optional[str] = None,
        wait_ms: int = 0,
        max_chars: int = 20000,
        working_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or "default"
        session = _ensure_session(session_id, working_dir=working_dir)
        default_wait_ms = wait_ms if wait_ms > 0 else 1000
        output = session.read(wait_ms=default_wait_ms, max_chars=max_chars)
        return {
            "success": True,
            "session_id": session_id,
            **output,
        }


class ShellStopTool(BaseTool):
    """Stop a shell session"""

    @property
    def name(self) -> str:
        return "shell_stop"

    @property
    def description(self) -> str:
        return "Stop a persistent bash session."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session/agent identifier for persistent shell",
                },
            },
            "required": [],
        }

    def execute(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        session_id = session_id or "default"
        session = _shell_sessions.get(session_id)
        if not session or not session.is_alive():
            return {
                "success": True,
                "session_id": session_id,
                "status": "stopped",
            }
        session.terminate()
        return {
            "success": True,
            "session_id": session_id,
            "status": "stopped",
        }


class ShellToolGroup(BaseToolGroup):
    """Shell tool group"""

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Persistent bash shell tools."

    def get_tools(self) -> List[BaseTool]:
        return [
            ShellStartTool(),
            ShellRunTool(),
            ShellWriteTool(),
            ShellReadTool(),
            ShellStopTool(),
        ]


class ShellStatus(BaseStatus):
    """Status provider for shell sessions"""

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Persistent bash shell status."

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "ok",
            "sessions": _get_sessions_status(),
        }
