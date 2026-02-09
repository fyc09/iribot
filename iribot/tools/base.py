"""Base tool class and interfaces"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Tool parameters schema"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the tool"""
        pass

    def to_dict(self) -> dict[str, Any]:
        """Convert tool to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class BaseToolGroup(ABC):
    """Abstract base class for tool groups"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool group name"""
        pass

    @property
    def description(self) -> str:
        """Tool group description"""
        return ""

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """Return tools in this group"""
        pass

class BaseStatus(ABC):
    """Abstract base class for status-only display"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Status name"""
        pass

    @property
    def description(self) -> str:
        """Status description"""
        return ""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return status for UI/health checks"""
        pass
