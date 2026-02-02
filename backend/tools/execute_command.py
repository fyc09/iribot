"""Execute command tool with interactive shell sessions"""
import os
import subprocess
import platform
import threading
import time
from collections import deque
from typing import Any, Dict, Optional, Deque, Tuple
from .base import BaseTool
from config import settings


class ShellSession:
    """Persistent shell session with async output capture"""

    def __init__(self, shell_type: str, working_dir: Optional[str] = None):
        self.shell_type = shell_type
        self.working_dir = working_dir
        self._output: Deque[Tuple[str, str]] = deque()
        self._log: Deque[Dict[str, str]] = deque()
        self._output_event = threading.Event()
        self._lock = threading.Lock()

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


_shell_sessions: Dict[str, ShellSession] = {}


class ExecuteCommandTool(BaseTool):
    """Interactive shell tool with per-session shells"""

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return (
            "Interactive Bash session. Actions: start, run, write, read, stop. "
            "Use session_id to keep a persistent shell per agent/session."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session/agent identifier for persistent shell"
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["start", "run", "write", "read", "stop"]
                },
                "command": {
                    "type": "string",
                    "description": "Command to run (for action: run)"
                },
                "input": {
                    "type": "string",
                    "description": "Input to write to stdin (for action: write)"
                },
                "wait_ms": {
                    "type": "integer",
                    "description": "Wait time in milliseconds before reading output (for action: read)",
                    "default": 0
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return from buffered output (for action: read)",
                    "default": 20000
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory to start shell (optional)"
                }
            },
            "required": []
        }

    def execute(
        self,
        session_id: Optional[str] = None,
        action: str = "run",
        command: Optional[str] = None,
        input: Optional[str] = None,
        wait_ms: int = 0,
        max_chars: int = 20000,
        working_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute an interactive shell action"""
        shell_type = "bash"
        session_id = session_id or "default"

        if action == "start":
            if session_id not in _shell_sessions or not _shell_sessions[session_id].is_alive():
                _shell_sessions[session_id] = ShellSession(shell_type, working_dir=working_dir)
                if working_dir:
                    _shell_sessions[session_id].write(f"cd {working_dir}")
            return {
                "success": True,
                "session_id": session_id,
                "shell_type": shell_type,
                "status": "started"
            }

        if session_id not in _shell_sessions or not _shell_sessions[session_id].is_alive():
            _shell_sessions[session_id] = ShellSession(shell_type, working_dir=working_dir)
            if working_dir:
                _shell_sessions[session_id].write(f"cd {working_dir}")

        session = _shell_sessions[session_id]

        if action == "run":
            if not command:
                return {"success": False, "error": "command is required for action=run"}
            
            # Use a unique marker to detect command completion
            import uuid
            marker = f"__CMD_DONE_{uuid.uuid4().hex[:8]}__"
            
            # Write command followed by echo marker
            session.write(command)
            session.write(f"echo {marker}")
            
            # Read output until marker appears or timeout
            max_wait_time = wait_ms if wait_ms > 0 else 10000  # Default 10 seconds
            start_time = time.time() * 1000
            all_stdout = []
            all_stderr = []
            marker_found = False
            
            while (time.time() * 1000 - start_time) < max_wait_time:
                output = session.read(wait_ms=500, max_chars=max_chars)
                stdout_chunk = output.get("stdout", "")
                stderr_chunk = output.get("stderr", "")
                
                if marker in stdout_chunk:
                    # Remove marker and everything after it
                    stdout_chunk = stdout_chunk.split(marker)[0]
                    marker_found = True
                
                if stdout_chunk:
                    all_stdout.append(stdout_chunk)
                if stderr_chunk:
                    all_stderr.append(stderr_chunk)
                    
                if marker_found:
                    break
                    
                # If no output, wait a bit before next read
                if not stdout_chunk and not stderr_chunk:
                    time.sleep(0.1)
            
            # Always return success: True since we executed the command
            # If there's an error, it will be in stderr
            return {
                "success": True,
                "session_id": session_id,
                "shell_type": shell_type,
                "stdout": "".join(all_stdout),
                "stderr": "".join(all_stderr),
            }

        if action == "write":
            if input is None:
                return {"success": False, "error": "input is required for action=write"}
            session.write(input)
            return {
                "success": True,
                "session_id": session_id,
                "shell_type": shell_type,
            }

        if action == "read":
            default_wait_ms = wait_ms if wait_ms > 0 else 1000
            output = session.read(wait_ms=default_wait_ms, max_chars=max_chars)
            return {
                "success": True,
                "session_id": session_id,
                "shell_type": shell_type,
                **output,
            }

        if action == "stop":
            session.terminate()
            return {
                "success": True,
                "session_id": session_id,
                "shell_type": shell_type,
                "status": "stopped"
            }

        return {"success": False, "error": f"Unknown action: {action}"}

    def get_status(self) -> Dict[str, Any]:
        sessions = []
        for session_id, session in _shell_sessions.items():
            sessions.append({
                "session_id": session_id,
                "shell_type": session.shell_type,
                "working_dir": session.working_dir,
                "alive": session.is_alive(),
                "pid": session.process.pid if session.process else None,
                "log": session.get_log(),
            })
        return {
            "name": self.name,
            "status": "ok",
            "sessions": sessions,
        }
