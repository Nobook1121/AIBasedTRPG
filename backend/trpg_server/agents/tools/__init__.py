from trpg_server.agents.tools.base import AgentTool, ToolRegistry
from trpg_server.agents.tools.dice import ROLL_COC_CHECK_TOOL, ROLL_ROOM_CHECK_TOOL, ROLL_DICE_TOOL, ROLL_DICE_FUNCTION_TOOL, ROLL_SANITY_CHECK_TOOL, ROLL_SANITY_CHECK_ALIAS_TOOL
from trpg_server.agents.tools.room import (
    GET_CHARACTER_CARDS_TOOL,
    GET_MEMORY_TOOL,
    GET_ROOM_SNAPSHOT_TOOL,
    GET_SCENARIO_CONTEXT_TOOL,
    GET_SCENARIO_MODULE_TOOL,
    ACTIVATE_SCENARIO_SCENE_TOOL,
    REMEMBER_FACT_TOOL,
)
from trpg_server.agents.tools.trigger import REVEAL_SCENARIO_TRIGGER_TOOL


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            GET_ROOM_SNAPSHOT_TOOL,
            GET_SCENARIO_CONTEXT_TOOL,
            GET_SCENARIO_MODULE_TOOL,
            ACTIVATE_SCENARIO_SCENE_TOOL,
            GET_CHARACTER_CARDS_TOOL,
            GET_MEMORY_TOOL,
            REMEMBER_FACT_TOOL,
            ROLL_COC_CHECK_TOOL,
            ROLL_ROOM_CHECK_TOOL,
            ROLL_SANITY_CHECK_TOOL,
            ROLL_SANITY_CHECK_ALIAS_TOOL,
            ROLL_DICE_TOOL,
            ROLL_DICE_FUNCTION_TOOL,
            REVEAL_SCENARIO_TRIGGER_TOOL,
        ]
    )
