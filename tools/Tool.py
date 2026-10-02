from abc import ABC, abstractmethod
from typing import Any

from agent.models import ToolCall, ToolResult

class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def definition(self) -> dict[str, Any]:
        """Return the LLM-facing tool schema."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool."""
        raise NotImplementedError