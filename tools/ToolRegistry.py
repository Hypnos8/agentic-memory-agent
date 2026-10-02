from agent.models import ToolCall, ToolResult
from tools.Tool import Tool
from typing import Any

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def definitions(self) -> list[dict[str, Any]]:
        return [
            tool.definition()
            for tool in self._tools.values()
        ]

    def execute(self, tool_call: ToolCall) -> ToolResult:
        tool = self._tools.get(tool_call.name)

        if tool is None:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Unknown tool: {tool_call.name}",
            )

        try:
            result = tool.execute(**tool_call.arguments)

            return ToolResult(
                tool_call_id=tool_call.id,
                success=True,
                content=str(result),
            )

        except TypeError as exc:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Invalid tool arguments: {exc}",
            )

        except Exception as exc:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"Tool execution failed: {exc}",
            )