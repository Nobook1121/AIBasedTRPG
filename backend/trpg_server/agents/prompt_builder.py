from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromptLayers:
    messages: list[dict[str, str]]
    cache_key: str
    static_prefix: str


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _versioned_id(value: dict[str, Any] | None, fallback: str) -> tuple[str, str]:
    data = value if isinstance(value, dict) else {}
    identifier = str(data.get("id") or data.get("scene_id") or fallback)
    version = str(data.get("version") or data.get("version_id") or "1")
    return identifier, version


def _scenario_static_content(scenario: dict[str, Any] | None) -> dict[str, Any]:
    data = scenario if isinstance(scenario, dict) else {}
    return {
        "id": data.get("id"),
        "version": data.get("version") or data.get("version_id") or "1",
        "core": data.get("core") or data.get("description") or data.get("notes") or "",
        "facts": data.get("facts") or data.get("core_facts") or [],
        "npcs": data.get("npcs") or data.get("key_npcs") or [],
        "rules": data.get("rules") or data.get("core_rules") or [],
    }


def _scene_static_content(scene: dict[str, Any] | None) -> dict[str, Any]:
    data = scene if isinstance(scene, dict) else {}
    return {
        "id": data.get("id") or data.get("scene_id"),
        "version": data.get("version") or data.get("version_id") or "1",
        "title": data.get("title") or "",
        "content": data.get("content") or data.get("description") or "",
        "events": data.get("events") or data.get("triggers") or [],
        "npcs": data.get("npcs") or [],
        "clues": data.get("clues") or [],
        "checks": data.get("checks") or data.get("judgement_table") or [],
    }


def build_prompt_layers(
    global_rules: str,
    scenario: dict[str, Any] | None,
    scene: dict[str, Any] | None,
    room_state: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
    user_input: str,
    rules_version: str = "1",
) -> PromptLayers:
    scenario_static = _scenario_static_content(scenario)
    scene_static = _scene_static_content(scene)
    scenario_id, scenario_version = _versioned_id(scenario, "unknown")
    scene_id, scene_version = _versioned_id(scene, "unknown")

    static_messages = [
        {"role": "system", "content": str(global_rules or "")},
        {"role": "system", "content": f"剧本静态核心：{_stable_json(scenario_static)}"},
        {"role": "system", "content": f"场景静态卡：{_stable_json(scene_static)}"},
    ]
    static_prefix = "\n".join(message["content"] for message in static_messages)

    dynamic_messages = [
        {
            "role": "system",
            "content": f"房间动态状态：{_stable_json(room_state if isinstance(room_state, dict) else {})}",
        }
    ]
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user")
        if role not in {"user", "assistant", "system"}:
            role = "user"
        dynamic_messages.append({"role": role, "content": str(item.get("content") or "")})
    dynamic_messages.append({"role": "user", "content": str(user_input or "")})

    return PromptLayers(
        messages=static_messages + dynamic_messages,
        cache_key=(
            f"scenario:{scenario_id}@{scenario_version}:"
            f"scene:{scene_id}@{scene_version}:rules:{str(rules_version)}"
        ),
        static_prefix=static_prefix,
    )
