import random
from collections.abc import Callable
from typing import Any

from trpg_server.agents.tools.base import AgentTool


def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _threshold(target: int, difficulty: str) -> int:
    if difficulty == "hard":
        return target // 2
    if difficulty == "extreme":
        return target // 5
    return target


def _success_level(roll: int, target: int) -> str:
    if roll == 1:
        return "critical"
    if roll <= target // 5:
        return "extreme"
    if roll <= target // 2:
        return "hard"
    if roll <= target:
        return "regular"
    if roll >= 96 and target < 50:
        return "fumble"
    if roll == 100:
        return "fumble"
    return "failure"


def roll_coc_check(arguments: dict[str, Any], rng: Callable[[int], int] | None = None) -> dict[str, Any]:
    roller = rng or (lambda sides: random.randint(1, sides))
    target = _as_int(arguments.get("target"))
    if target < 1 or target > 100:
        return {"error": "target must be between 1 and 100"}

    difficulty = str(arguments.get("difficulty") or "regular").lower()
    if difficulty not in {"regular", "hard", "extreme"}:
        return {"error": "difficulty must be regular, hard, or extreme"}

    roll = roller(100)
    threshold = _threshold(target, difficulty)
    level = _success_level(roll, target)
    success = roll <= threshold or level == "critical"
    if level == "fumble":
        success = False

    skill = str(arguments.get("skill") or "检定")
    reason = str(arguments.get("reason") or "")
    summary = f"{skill}检定：1d100={roll}，目标{target}，{difficulty}难度阈值{threshold}，结果：{level}。"
    if reason:
        summary += f" 原因：{reason}。"

    return {
        "skill": skill,
        "reason": reason,
        "roll": roll,
        "target": target,
        "difficulty": difficulty,
        "threshold": threshold,
        "success": success,
        "success_level": level if success else "failure",
        "raw_success_level": level,
        "critical": roll == 1,
        "fumble": level == "fumble",
        "summary": summary,
    }


def execute_roll_coc_check(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    return roll_coc_check(arguments)


ROLL_COC_CHECK_TOOL = AgentTool(
    name="dice.roll_coc_check",
    description="Roll a real backend COC7 percentile check. The model must not invent dice results.",
    parameters={
        "type": "object",
        "properties": {
            "character_name": {"type": "string"},
            "skill": {"type": "string"},
            "target": {"type": "integer", "minimum": 1, "maximum": 100},
            "difficulty": {"type": "string", "enum": ["regular", "hard", "extreme"]},
            "reason": {"type": "string"},
        },
        "required": ["skill", "target"],
    },
    handler=execute_roll_coc_check,
)
