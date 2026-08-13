from pathlib import Path

from trpg_server.permission_config import (
    DEFAULT_ROLE_ORDER,
    default_permission_config,
    is_role_allowed,
    load_permission_config,
    save_permission_config,
)


def test_default_permission_config_groups_nodes_by_site_area():
    config = default_permission_config()

    group_ids = {group["id"] for group in config["groups"]}
    node_ids = {node["id"] for group in config["groups"] for node in group["nodes"]}

    assert {"accounts", "scenarios", "characters", "settings"}.issubset(group_ids)
    assert {
        "accounts.manage_users",
        "scenarios.manage_all",
        "characters.manage_all",
        "settings.permissions",
        "settings.ai_models",
        "settings.network",
    }.issubset(node_ids)
    assert config["roles"] == DEFAULT_ROLE_ORDER


def test_load_permission_config_merges_saved_matrix_without_losing_new_nodes(tmp_path: Path):
    config_path = tmp_path / "permissions.json"
    save_permission_config(
        config_path,
        {
            "matrix": {
                "settings.permissions": ["OWNER"],
                "scenarios.manage_all": ["ADMIN", "OWNER"],
            }
        },
    )

    loaded = load_permission_config(config_path)

    assert loaded["matrix"]["settings.permissions"] == ["OWNER"]
    assert loaded["matrix"]["scenarios.manage_all"] == ["ADMIN", "OWNER"]
    assert "characters.manage_own" in loaded["matrix"]


def test_permission_check_uses_configurable_nodes(tmp_path: Path):
    config_path = tmp_path / "permissions.json"
    save_permission_config(
        config_path,
        {"matrix": {"settings.permissions": ["OWNER"], "settings.general": ["USER", "ADMIN", "OWNER"]}},
    )

    assert is_role_allowed("OWNER", "settings.permissions", config_path)
    assert not is_role_allowed("ADMIN", "settings.permissions", config_path)
    assert is_role_allowed("USER", "settings.general", config_path)
