from trpg_server.agents.tools.base import AgentTool, ToolRegistry
from trpg_server.agents.tools.dice import ROLL_COC_CHECK_TOOL


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry([ROLL_COC_CHECK_TOOL])
