from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from trpg_server.json_store import read_json, write_json_atomic


def _platform_config_copy(config: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(config) if isinstance(config, dict) else {}


def split_platform_config(config: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    public_config = _platform_config_copy(config)
    config_section = public_config.get("config")
    if not isinstance(config_section, dict):
        return public_config, None

    api_key = config_section.pop("api_key", None)
    if api_key in (None, ""):
        return public_config, None

    return public_config, {"api_key": str(api_key)}


def merge_platform_config(
    public_config: dict[str, Any] | None,
    secret_config: dict[str, Any] | None,
) -> dict[str, Any]:
    merged_config = _platform_config_copy(public_config)
    if not isinstance(secret_config, dict):
        return merged_config

    api_key = secret_config.get("api_key")
    if api_key in (None, ""):
        return merged_config

    config_section = merged_config.setdefault("config", {})
    if isinstance(config_section, dict):
        config_section["api_key"] = str(api_key)
    return merged_config


def load_public_platform_config(public_path: Path, secret_path: Path | None = None) -> dict[str, Any]:
    raw_config = read_json(public_path, default={})
    public_config, secret_config = split_platform_config(raw_config)

    if secret_path and secret_config:
        write_json_atomic(secret_path, secret_config)
        write_json_atomic(public_path, public_config)
    elif raw_config != public_config:
        write_json_atomic(public_path, public_config)

    return public_config


def load_platform_config(public_path: Path, secret_path: Path | None = None) -> dict[str, Any]:
    public_config = load_public_platform_config(public_path, secret_path)
    secret_config = read_json(secret_path, default={}) if secret_path and secret_path.exists() else {}
    return merge_platform_config(public_config, secret_config)


def save_platform_config(
    public_path: Path,
    secret_path: Path | None,
    config: dict[str, Any] | None,
) -> dict[str, Any]:
    public_config, secret_config = split_platform_config(config)
    write_json_atomic(public_path, public_config)
    if secret_path:
        existing_secret = read_json(secret_path, default={}) if secret_path.exists() else {}
        if secret_config is None and isinstance(existing_secret, dict):
            existing_api_key = existing_secret.get("api_key")
            if existing_api_key not in (None, ""):
                secret_config = {"api_key": str(existing_api_key)}
        if secret_config is not None:
            write_json_atomic(secret_path, secret_config)
    return public_config
