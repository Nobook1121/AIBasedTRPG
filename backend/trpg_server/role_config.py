from __future__ import annotations

from pathlib import Path
from typing import Any

from trpg_server.json_store import read_json, write_json_atomic


DEFAULT_ROLE_ID = "kp"


def enabled_providers(platform_dir: Path) -> dict[str, dict[str, Any]]:
    if not platform_dir.exists():
        return {}

    providers: dict[str, dict[str, Any]] = {}
    for path in sorted(platform_dir.glob("*.json")):
        config = read_json(path, default={})
        if config.get("enabled", False):
            providers[path.stem] = config
    return providers


def enabled_provider_options(platform_dir: Path) -> list[dict[str, str]]:
    return [
        {"id": provider_id, "name": str(config.get("name") or provider_id)}
        for provider_id, config in enabled_providers(platform_dir).items()
    ]


def load_prompt_text(prompt_file: Path) -> str:
    if not prompt_file.exists():
        return "你是KP（守密人），负责主持TRPG游戏，引导玩家进行游戏。"

    content = prompt_file.read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if not line.startswith("#") and line.strip()]
    return "\n".join(lines) if lines else "你是KP（守密人），负责主持TRPG游戏，引导玩家进行游戏。"


def default_roles(prompt_file: Path, platform_dir: Path) -> list[dict[str, Any]]:
    provider = next(iter(enabled_providers(platform_dir)), "")
    return [
        {
            "id": DEFAULT_ROLE_ID,
            "name": "KP",
            "wake_words": ["@KP"],
            "prompt": load_prompt_text(prompt_file),
            "provider": provider,
        }
    ]


def normalize_roles(
    roles: list[dict[str, Any]],
    prompt_file: Path,
    platform_dir: Path,
) -> list[dict[str, Any]]:
    provider_ids = set(enabled_providers(platform_dir))
    fallback_provider = next(iter(provider_ids), "")
    normalized: list[dict[str, Any]] = []

    for role in roles:
        role_id = str(role.get("id") or "").strip().lower()
        if not role_id:
            continue

        wake_words = [
            str(wake_word).strip()
            for wake_word in role.get("wake_words", [])
            if str(wake_word).strip()
        ]
        provider = str(role.get("provider") or "").strip()
        if provider and provider not in provider_ids:
            provider = fallback_provider

        normalized.append(
            {
                "id": role_id,
                "name": str(role.get("name") or role_id.upper()).strip(),
                "wake_words": wake_words or [f"@{role_id.upper()}"],
                "prompt": str(role.get("prompt") or load_prompt_text(prompt_file)),
                "provider": provider or fallback_provider,
            }
        )

    return normalized or default_roles(prompt_file, platform_dir)


def load_roles(role_config_file: Path, prompt_file: Path, platform_dir: Path) -> list[dict[str, Any]]:
    if not role_config_file.exists():
        return default_roles(prompt_file, platform_dir)

    data = read_json(role_config_file, default={})
    return normalize_roles(data.get("roles", []), prompt_file, platform_dir)


def save_role(
    role_config_file: Path,
    prompt_file: Path,
    platform_dir: Path,
    role_id: str,
    update: dict[str, Any],
) -> list[dict[str, Any]]:
    role_id = role_id.strip().lower()
    provider = str(update.get("provider") or "").strip()
    if provider not in enabled_providers(platform_dir):
        raise ValueError("Role provider must be an enabled AI provider")

    wake_words = update.get("wake_words")
    if not isinstance(wake_words, list) or not any(str(item).strip() for item in wake_words):
        raise ValueError("Role wake words are required")

    prompt = update.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Role prompt is required")

    roles = load_roles(role_config_file, prompt_file, platform_dir)
    existing = next((role for role in roles if role["id"] == role_id), None)
    if existing is None:
        existing = {"id": role_id, "name": role_id.upper()}
        roles.append(existing)

    existing.update(
        {
            "name": str(update.get("name") or existing.get("name") or role_id.upper()).strip(),
            "wake_words": [str(item).strip() for item in wake_words if str(item).strip()],
            "prompt": prompt,
            "provider": provider,
        }
    )

    role_config_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(role_config_file, {"roles": roles})
    return roles


def select_role_for_content(roles: list[dict[str, Any]], content: str) -> dict[str, Any]:
    normalized_content = content.strip()
    for role in roles:
        for wake_word in role.get("wake_words", []):
            if normalized_content.startswith(str(wake_word)):
                return role
    return roles[0]
