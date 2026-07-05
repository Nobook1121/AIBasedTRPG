from trpg_server.agents.tools.base import AgentTool, ToolRegistry
from trpg_server.agents.tools.dice import ROLL_COC_CHECK_TOOL
from trpg_server.agents.tools.room import (
    GET_CHARACTER_CARDS_TOOL,
    GET_MEMORY_TOOL,
    GET_ROOM_SNAPSHOT_TOOL,
    GET_SCENARIO_CONTEXT_TOOL,
    REMEMBER_FACT_TOOL,
)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            GET_ROOM_SNAPSHOT_TOOL,
            GET_SCENARIO_CONTEXT_TOOL,
            GET_CHARACTER_CARDS_TOOL,
            GET_MEMORY_TOOL,
            REMEMBER_FACT_TOOL,
            ROLL_COC_CHECK_TOOL,
        ]
    )
