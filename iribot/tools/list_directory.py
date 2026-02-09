"""List directory tool"""
from pathlib import Path
from typing import Any

from .base import BaseTool


class ListDirectoryTool(BaseTool):
    """List files and directories"""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories in a path"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to list"
                }
            },
            "required": ["path"]
        }

    def execute(self, path: str) -> dict[str, Any]:
        """List directory contents"""
        try:
            items = [
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item)
                }
                for item in Path(path).iterdir()
            ]
            return {
                "success": True,
                "items": items
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
