import logging
import random
from collections.abc import Callable
from typing import Any

from trpg_server.agents.tools.base import AgentTool

logger = logging.getLogger(__name__)

DIFFICULTY_ALIASES = {
    "regular": "regular",
    "普通": "regular",
    "hard": "hard",
    "困难": "hard",
    "extreme": "extreme",
    "极难": "extreme",
}
DIFFICULTY_LABELS = {
    "regular": "",
    "hard": "困难",
    "extreme": "极难",
}
ATTRIBUTE_ALIASES = {
    "STR": "STR",
    "力量": "STR",
    "CON": "CON",
    "体质": "CON",
    "SIZ": "SIZ",
    "体型": "SIZ",
    "DEX": "DEX",
    "敏捷": "DEX",
    "APP": "APP",
    "外貌": "APP",
    "INT": "INT",
    "智力": "INT",
    "POW": "POW",
    "意志": "POW",
    "EDU": "EDU",
    "教育": "EDU",
    "LUC": "LUC",
    "幸运": "LUC",
    "AGE": "AGE",
    "年龄": "AGE",
}


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


def _normalize_difficulty(value: Any) -> str:
    difficulty = str(value or "regular").strip()
    return DIFFICULTY_ALIASES.get(difficulty, DIFFICULTY_ALIASES.get(difficulty.lower(), ""))


def _adjust_threshold(threshold: int, adjustment: Any) -> int:
    text = str(adjustment or "").strip()
    if not text:
        return threshold
    if not (text.startswith("+") or text.startswith("-")):
        raise ValueError("adjustment must start with + or -")
    amount = int(text[1:])
    return threshold + amount if text.startswith("+") else threshold - amount


def _active_members(context: Any) -> list[dict[str, Any]]:
    info = context.room_info()
    members = info.get("members", [])
    return [member for member in members if isinstance(member, dict)]


def _find_member(player_name: str, context: Any) -> dict[str, Any] | None:
    expected = player_name.casefold()
    for member in _active_members(context):
        active = member.get("is_active", True) is not False and member.get("status", "active") != "removed"
        if active and str(member.get("username") or "").casefold() == expected:
            return member
    return None


def _lookup_check_value(card: dict[str, Any], check_name: str) -> int | None:
    attributes = card.get("attributes")
    attribute_key = ATTRIBUTE_ALIASES.get(check_name) or ATTRIBUTE_ALIASES.get(check_name.upper())
    if isinstance(attributes, dict) and attribute_key:
        value = attributes.get(attribute_key)
        if value is not None:
            return _as_int(value, -1)

    expected = check_name.casefold()
    skills = card.get("skills")
    if isinstance(skills, list):
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            names = [skill.get("name"), skill.get("skillKey"), skill.get("id")]
            if any(str(name or "").casefold() == expected for name in names):
                return _as_int(skill.get("value"), -1)
    return None


def _format_room_check_summary(name: str, difficulty: str, roll: int, threshold: int, success: bool) -> str:
    prefix = DIFFICULTY_LABELS[difficulty]
    result_text = "成功" if success else "失败"
    return f"{prefix}{name} d%: [{roll}] = {roll} / {threshold} {result_text}"


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


def roll_room_check(
    arguments: dict[str, Any],
    context: Any,
    rng: Callable[[int], int] | None = None,
) -> dict[str, Any]:
    player_name = str(arguments.get("player_name") or arguments.get("playerName") or "").strip()
    check_name = str(arguments.get("name") or arguments.get("skill") or "").strip()
    if not player_name:
        return {"error": "player_name is required"}
    if not check_name:
        return {"error": "name is required"}

    difficulty = _normalize_difficulty(arguments.get("difficulty"))
    if not difficulty:
        return {"error": "difficulty must be regular, hard, extreme, 普通, 困难, or 极难"}

    try:
        member = _find_member(player_name, context)
        if not member:
            return {"error": f"player {player_name} was not found in current room"}
        card = member.get("character_card")
        if not isinstance(card, dict):
            return {"error": f"player {player_name} has no bound character card"}
        base_target = _lookup_check_value(card, check_name)
        if base_target is None or base_target < 0:
            return {"error": f"{check_name} was not found on player {player_name}'s character card"}
        if base_target > 100:
            return {"error": f"{check_name} value must be between 0 and 100"}
        threshold = _threshold(base_target, difficulty)
        threshold = _adjust_threshold(threshold, arguments.get("adjustment"))
    except ValueError as exc:
        return {"error": str(exc)}

    roller = rng or (lambda sides: random.randint(1, sides))
    roll = roller(100)
    success = roll <= threshold
    summary = _format_room_check_summary(check_name, difficulty, roll, threshold, success)
    logger.info(
        "room check rolled",
        extra={
            "player_name": player_name,
            "check_name": check_name,
            "difficulty": difficulty,
            "base_target": base_target,
            "threshold": threshold,
            "roll": roll,
            "success": success,
        },
    )
    return {
        "player_name": player_name,
        "character_name": card.get("name"),
        "name": check_name,
        "roll": roll,
        "base_target": base_target,
        "target": threshold,
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_LABELS[difficulty],
        "adjustment": str(arguments.get("adjustment") or "").strip(),
        "threshold": threshold,
        "success": success,
        "summary": summary,
    }


def execute_roll_room_check(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    return roll_room_check(arguments, context)


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

ROLL_ROOM_CHECK_TOOL = AgentTool(
    name="check.roll_room_check",
    description=(
        "Resolve a current-room player's bound character_card by username, read a skill or attribute value, "
        "roll 1d100, and return the formatted /check result. Use this for /check {*玩家名} {*技能/属性名} "
        "{困难/极难} {+/-调整值}."
    ),
    parameters={
        "type": "object",
        "properties": {
            "player_name": {"type": "string", "description": "Current room member username."},
            "name": {"type": "string", "description": "Skill or attribute name, e.g. 侦察 or 敏捷."},
            "difficulty": {"type": "string", "enum": ["regular", "hard", "extreme", "普通", "困难", "极难"]},
            "adjustment": {"type": "string", "description": "Optional signed adjustment such as +10 or -20."},
        },
        "required": ["player_name", "name"],
    },
    handler=execute_roll_room_check,
)
