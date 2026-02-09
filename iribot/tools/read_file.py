"""Read file tool"""
from typing import Any

from .base import BaseTool


class ReadFileTool(BaseTool):
    """Read content from files"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read content from a file"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["file_path"]
        }

    def execute(self, file_path: str) -> dict[str, Any]:
        """Read file content"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
