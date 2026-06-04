import json

import user_manager as user_manager_module
from user_manager import UserManager


def test_save_users_creates_missing_parent_directory(tmp_path, monkeypatch):
    users_file = tmp_path / "nested" / "users.json"
    monkeypatch.setattr(user_manager_module, "USERS_FILE", users_file)
    manager = UserManager()
    manager.users = [
        {"id": 1, "username": "owner", "role": "OWNER", "status": "active"}
    ]

    assert manager._save_users() is True
    data = json.loads(users_file.read_text(encoding="utf-8"))
    assert data["users"][0]["username"] == "owner"


def test_create_ip_config_creates_missing_directory(tmp_path, monkeypatch):
    config_dir = tmp_path / "ip_configs"
    monkeypatch.setattr(user_manager_module, "USER_IP_CONFIG_DIR", config_dir)
    manager = UserManager()

    assert manager.create_ip_config("127.0.0.1") is True
    assert (config_dir / "127_0_0_1.json").exists()


def test_create_ip_config_keeps_unsafe_ip_inside_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / "ip_configs"
    monkeypatch.setattr(user_manager_module, "USER_IP_CONFIG_DIR", config_dir)
    manager = UserManager()

    assert manager.create_ip_config("127.0.0.1/../../escape") is True

    created_files = list(config_dir.glob("*.json"))
    assert len(created_files) == 1
    assert created_files[0].parent == config_dir
    assert not (tmp_path / "escape.json").exists()


def test_check_permission_owner_has_admin_access():
    manager = UserManager()
    manager.users = [{"id": 1, "username": "owner", "role": "OWNER", "status": "active"}]

    assert manager.check_permission(1, "ADMIN")


def test_check_permission_user_lacks_admin_access():
    manager = UserManager()
    manager.users = [{"id": 1, "username": "user", "role": "USER", "status": "active"}]

    assert not manager.check_permission(1, "ADMIN")
