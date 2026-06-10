import importlib

import user_manager as user_manager_module
from trpg_server.users.service import UserService


def test_user_manager_import_has_no_filesystem_side_effects(tmp_path, monkeypatch):
    users_file = tmp_path / "users.json"
    database_file = tmp_path / "users.sqlite3"
    ip_config_dir = tmp_path / "ip_configs"
    monkeypatch.setenv("AI_TRPG_USER_DATABASE_FILE", str(database_file))
    monkeypatch.setenv("AI_TRPG_USERS_FILE", str(users_file))
    monkeypatch.setenv("AI_TRPG_USER_IP_CONFIG_DIR", str(ip_config_dir))

    importlib.reload(user_manager_module)

    assert users_file.exists() is False
    assert database_file.exists() is False
    assert ip_config_dir.exists() is False


def test_user_manager_lazy_wrapper_delegates_to_user_service(tmp_path):
    manager = user_manager_module.UserManager(
        database_file=tmp_path / "users.sqlite3",
        users_file=tmp_path / "users.json",
        ip_config_dir=tmp_path / "ip_configs",
    )

    ok, message, user = manager.register(
        "Alice",
        "StrongPass1",
        "alice@example.com",
        terms_accepted=True,
    )

    assert ok is True
    assert isinstance(manager._get_service(), UserService)
    assert manager.get_user_by_id(user["id"])["username"] == "Alice"
