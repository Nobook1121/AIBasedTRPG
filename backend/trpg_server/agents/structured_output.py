from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trpg_server.agents.room_state import load_room_state, save_room_state


@dataclass(frozen=True)
class StructuredKPResponse:
    narration: str = ""
    options: list[str] = field(default_factory=list)
    state_updates: dict[str, Any] = field(default_factory=dict)
    next_scene: str | None = None
    npc_actions: list[dict[str, Any]] = field(default_factory=list)


def _extract_json_object(content: str) -> dict[str, Any] | None:
    text = str(content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(text[start : end + 1])
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def parse_kp_response(content: str) -> StructuredKPResponse | None:
    data = _extract_json_object(content)
    if not data or not any(key in data for key in ("narration", "options", "state_updates", "next_scene", "npc_actions")):
        return None
    options = data.get("options") if isinstance(data.get("options"), list) else []
    actions = data.get("npc_actions") if isinstance(data.get("npc_actions"), list) else []
    updates = data.get("state_updates") if isinstance(data.get("state_updates"), dict) else {}
    return StructuredKPResponse(
        narration=str(data.get("narration") or "").strip(),
        options=[str(item).strip()[:200] for item in options if str(item).strip()][:8],
        state_updates=updates,
        next_scene=str(data.get("next_scene")).strip() if data.get("next_scene") not in (None, "") else None,
        npc_actions=[item for item in actions if isinstance(item, dict)][:20],
    )


ALLOWED_STATE_FIELDS = {
    "active_scene_id",
    "triggered_event_ids",
    "clues",
    "npc_attitudes",
    "items",
    "quests",
    "timeline",
    "rolling_summary",
}


def validate_state_updates(
    updates: dict[str, Any] | None,
    room_state: dict[str, Any] | None,
    scenario: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(updates, dict):
        return {}
    result: dict[str, Any] = {}
    scenario_data = scenario if isinstance(scenario, dict) else {}
    manifest = scenario_data.get("scene_manifest") if isinstance(scenario_data.get("scene_manifest"), list) else []
    scene_ids = {str(item.get("id") or item.get("module_id")) for item in manifest if isinstance(item, dict)}
    for key, value in updates.items():
        if key not in ALLOWED_STATE_FIELDS:
            continue
        if key == "active_scene_id":
            if value not in (None, "") and str(value) not in scene_ids:
                continue
            result[key] = str(value) if value not in (None, "") else None
        elif key == "npc_attitudes":
            if isinstance(value, dict):
                result[key] = {str(k)[:100]: str(v)[:200] for k, v in value.items()} 
        elif key == "rolling_summary":
            result[key] = str(value or "")[:4000]
        elif isinstance(value, list):
            result[key] = value[:50]
    return result


def apply_state_updates(room_dir: Path, updates: dict[str, Any]) -> dict[str, Any]:
    state = load_room_state(room_dir)
    state.update(updates)
    return save_room_state(room_dir, state)
