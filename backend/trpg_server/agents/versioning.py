"""Scenario release and room binding helpers."""

from __future__ import annotations

from typing import Any, Iterable, Mapping
import copy
import re

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

def normalize_semver(value: Any, default: str = "1.0.0") -> str:
    text = str(value or "").strip()
    match = SEMVER_RE.fullmatch(text)
    if match: return ".".join(str(int(part)) for part in match.groups())
    if text.isdigit(): return f"1.0.{int(text)}"
    return default


def next_scenario_version(current: Any) -> str:
    text = str(current or "").strip()
    match = SEMVER_RE.fullmatch(text)
    if match:
        major, minor, patch = (int(part) for part in match.groups())
        return f"{major}.{minor}.{patch + 1}"
    try:
        return str(int(text) + 1)
    except (TypeError, ValueError):
        return "1"

def scenario_content_changed(old: Mapping[str, Any] | None, new: Mapping[str, Any] | None) -> bool:
    def stable(value):
        if not isinstance(value, Mapping): return value
        result = copy.deepcopy(dict(value))
        for key in ("id", "scenario_version", "version", "version_id", "createdAt", "updatedAt", "owner_id", "creator_username", "public_id"):
            result.pop(key, None)
        return result
    return stable(old or {}) != stable(new or {})


def scenario_version(scenario: Mapping[str, Any] | None) -> str:
    data = scenario if isinstance(scenario, Mapping) else {}
    return str(data.get("scenario_version") or data.get("version") or data.get("version_id") or "1")


def bind_room_to_scenario_version(room: Mapping[str, Any], scenario: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(room)
    result["scenario_id"] = scenario.get("id")
    result["scenario_version"] = scenario_version(scenario)
    return result


def validate_version_migration(mapping: Mapping[str, Any] | None, old_entities: Iterable[Any], new_entities: Iterable[Any]) -> dict[str, Any]:
    mapping = mapping if isinstance(mapping, Mapping) else {}
    old_set = {str(item) for item in old_entities}
    new_set = {str(item) for item in new_entities}
    missing = sorted(entity for entity in old_set if entity not in mapping and entity not in new_set)
    invalid = sorted(str(target) for source, target in mapping.items() if str(source) in old_set and str(target) not in new_set)
    return {"valid": not missing and not invalid, "missing": missing, "invalid": invalid}


def migrate_room_binding(
    room: Mapping[str, Any],
    target_scenario: Mapping[str, Any],
    mapping: Mapping[str, Any] | None,
    old_entities: Iterable[Any],
    new_entities: Iterable[Any],
) -> dict[str, Any]:
    check = validate_version_migration(mapping, old_entities, new_entities)
    if not check["valid"]:
        raise ValueError(f"scenario migration rejected: {check}")
    result = dict(room)
    result["scenario_id"] = target_scenario.get("id")
    result["scenario_version"] = scenario_version(target_scenario)
    result["migration"] = {"mapping": dict(mapping or {}), "from_version": room.get("scenario_version"), "to_version": result["scenario_version"]}
    return result
