from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.settings import CONFIG_DIR

DEFAULT_ROLE_ORDER = ["USER", "ADMIN", "OWNER"]
PERMISSION_CONFIG_FILENAME = "permissions.json"

DEFAULT_PERMISSION_GROUPS: list[dict[str, Any]] = [
    {
        "id": "accounts",
        "label": "账户管理",
        "description": "用户列表、用户状态、角色分配与认证策略。",
        "nodes": [
            {"id": "accounts.manage_users", "label": "管理用户", "description": "查看用户列表并修改角色或状态。"},
            {"id": "accounts.auth_settings", "label": "认证设置", "description": "配置注册、登录和认证相关策略。"},
        ],
    },
    {
        "id": "scenarios",
        "label": "剧本管理",
        "description": "剧本创建、编辑、删除和跨用户管理。",
        "nodes": [
            {"id": "scenarios.create", "label": "创建剧本", "description": "创建和导入自己的剧本。"},
            {"id": "scenarios.manage_own", "label": "管理自己的剧本", "description": "编辑或删除自己拥有的剧本。"},
            {"id": "scenarios.manage_all", "label": "管理全部剧本", "description": "编辑或删除任意用户的剧本。"},
        ],
    },
    {
        "id": "characters",
        "label": "角色卡管理",
        "description": "角色卡创建、编辑、删除和跨用户管理。",
        "nodes": [
            {"id": "characters.create", "label": "创建角色卡", "description": "创建自己的角色卡。"},
            {"id": "characters.manage_own", "label": "管理自己的角色卡", "description": "编辑或删除自己拥有的角色卡。"},
            {"id": "characters.manage_all", "label": "管理全部角色卡", "description": "编辑或删除任意用户的角色卡。"},
        ],
    },
    {
        "id": "settings",
        "label": "设置",
        "description": "常规设置、模型设置、网络设置、角色卡规则和权限矩阵。",
        "nodes": [
            {"id": "settings.general", "label": "常规设置", "description": "保存主题、语言、通知、聊天等常规配置。"},
            {"id": "settings.ai_models", "label": "模型设置", "description": "配置 AI 平台、模型请求和 AI 角色。"},
            {"id": "settings.network", "label": "网络配置", "description": "保存端口、局域网发现和连接测试配置。"},
            {"id": "settings.character_rules", "label": "角色卡规则", "description": "配置角色卡数量、属性规则和武器栏位。"},
            {"id": "settings.permissions", "label": "权限配置", "description": "配置各等级用户可以使用的网站权限。"},
        ],
    },
    {
        "id": "rooms",
        "label": "房间管理",
        "description": "房间创建、成员管理、回档和运行时记录。",
        "nodes": [
            {"id": "rooms.create", "label": "创建房间", "description": "创建跑团房间。"},
            {"id": "rooms.manage_members", "label": "管理房间成员", "description": "绑定角色、移除成员和提升房间权限。"},
            {"id": "rooms.runtime_records", "label": "运行时记录", "description": "记录或删除伤害、San 值等运行时变化。"},
        ],
    },
]

DEFAULT_PERMISSION_MATRIX: dict[str, list[str]] = {
    "accounts.manage_users": ["ADMIN", "OWNER"],
    "accounts.auth_settings": ["ADMIN", "OWNER"],
    "scenarios.create": ["USER", "ADMIN", "OWNER"],
    "scenarios.manage_own": ["USER", "ADMIN", "OWNER"],
    "scenarios.manage_all": ["ADMIN", "OWNER"],
    "characters.create": ["USER", "ADMIN", "OWNER"],
    "characters.manage_own": ["USER", "ADMIN", "OWNER"],
    "characters.manage_all": ["ADMIN", "OWNER"],
    "settings.general": ["ADMIN", "OWNER"],
    "settings.ai_models": ["ADMIN", "OWNER"],
    "settings.network": ["ADMIN", "OWNER"],
    "settings.character_rules": ["ADMIN", "OWNER"],
    "settings.permissions": ["OWNER"],
    "rooms.create": ["USER", "ADMIN", "OWNER"],
    "rooms.manage_members": ["ADMIN", "OWNER"],
    "rooms.runtime_records": ["USER", "ADMIN", "OWNER"],
}


def permission_config_path(config_dir: Path | None = None) -> Path:
    return Path(config_dir or CONFIG_DIR) / PERMISSION_CONFIG_FILENAME


def permission_node_ids() -> set[str]:
    return {str(node["id"]) for group in DEFAULT_PERMISSION_GROUPS for node in group["nodes"]}


def default_permission_config() -> dict[str, Any]:
    return {
        "roles": list(DEFAULT_ROLE_ORDER),
        "groups": deepcopy(DEFAULT_PERMISSION_GROUPS),
        "matrix": deepcopy(DEFAULT_PERMISSION_MATRIX),
    }


def normalize_permission_config(data: dict[str, Any] | None) -> dict[str, Any]:
    normalized = default_permission_config()
    if not isinstance(data, dict):
        return normalized

    matrix = data.get("matrix")
    if not isinstance(matrix, dict):
        return normalized

    node_ids = permission_node_ids()
    for node_id, roles in matrix.items():
        if node_id not in node_ids or not isinstance(roles, list):
            continue
        filtered = [role for role in DEFAULT_ROLE_ORDER if role in {str(item) for item in roles}]
        normalized["matrix"][node_id] = filtered
    return normalized


def load_permission_config(config_path: Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path is not None else permission_config_path()
    return normalize_permission_config(read_json(path, default={}))


def save_permission_config(config_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    config = normalize_permission_config(data)
    write_json_atomic(config_path, {"matrix": config["matrix"]})
    return config


def is_role_allowed(role: str, node_id: str, config_path: Path | None = None) -> bool:
    config = load_permission_config(config_path)
    return str(role or "USER") in config["matrix"].get(node_id, [])
