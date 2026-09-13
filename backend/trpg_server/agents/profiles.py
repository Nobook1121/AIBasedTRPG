from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_KP_TOOLS = [
    "room.get_room_snapshot",
    "room.get_scenario_context",
    "room.get_scenario_module",
    "room.activate_scenario_scene",
    "room.get_character_cards",
    "room.get_memory",
    "room.remember_fact",
    "dice.roll_coc_check",
    "dice.roll",
    "dice.roll_dice",
    "check.roll_room_check",
    "san.roll_sanity_check",
    "sanity.roll_sanity_check",
    "trigger.reveal_scenario_trigger",
]


@dataclass(frozen=True)
class AgentProfile:
    id: str
    name: str
    prompt: str
    provider: str | None = None
    wake_words: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)
    context_providers: list[str] = field(default_factory=list)


def resolve_agent_profile(
    role: dict[str, Any],
    prompt_file: Path,
    *,
    prefer_prompt_file: bool = False,
) -> AgentProfile:
    role_id = str(role.get("id") or "kp")
    prompt = str(role.get("prompt") or "")
    if role_id == "kp" and prompt_file.exists() and (prefer_prompt_file or not prompt):
        prompt = prompt_file.read_text(encoding="utf-8")

    configured_tools = role.get("tools")
    if isinstance(configured_tools, list):
        tool_names = [str(name) for name in configured_tools if str(name).strip()]
    elif role_id == "kp":
        tool_names = DEFAULT_KP_TOOLS.copy()
    else:
        tool_names = []

    configured_context = role.get("context")
    context_providers = (
        [str(name) for name in configured_context if str(name).strip()]
        if isinstance(configured_context, list)
        else []
    )

    return AgentProfile(
        id=role_id,
        name=str(role.get("name") or role_id),
        prompt=prompt,
        provider=role.get("provider"),
        wake_words=[str(word) for word in role.get("wake_words", [])],
        tool_names=tool_names,
        context_providers=context_providers,
    )
