from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ToolExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any], Any], dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self, tools: list[AgentTool] | None = None):
        self._tools = {tool.name: tool for tool in tools or []}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def select(self, names: list[str]) -> list[AgentTool]:
        return [self._tools[name] for name in names if name in self._tools]

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)
