"""Write file tool"""
from pathlib import Path
from typing import Any

from .base import BaseTool


class WriteFileTool(BaseTool):
    """Write content to files"""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }

    def execute(self, file_path: str, content: str) -> dict[str, Any]:
        """Write content to file"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {
                "success": True,
                "message": f"File written successfully: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
