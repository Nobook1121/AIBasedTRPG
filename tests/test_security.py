import pytest
from flask import Flask

from trpg_server.security import (
    ACTIVE_SESSION_REGISTRY_KEY,
    SESSION_TOKEN_KEY,
    build_public_asset_url,
    is_allowed_upload,
    normalize_filename,
    require_permission,
    register_session_guard,
    safe_join,
)


def test_safe_join_allows_child_path(tmp_path):
    result = safe_join(tmp_path, "covers", "cover.png")

    assert result == tmp_path / "covers" / "cover.png"


def test_safe_join_rejects_parent_escape(tmp_path):
    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(tmp_path, "..", "users.json")


def test_safe_join_rejects_absolute_path_outside_base(tmp_path):
    base = tmp_path / "base"
    outside = tmp_path / "outside" / "file.txt"

    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(base, outside)


def test_safe_join_rejects_sibling_prefix_escape(tmp_path):
    base = tmp_path / "base"
    outside = tmp_path / "base_evil" / "file.txt"

    with pytest.raises(ValueError, match="Unsafe path"):
        safe_join(base, outside)


def test_is_allowed_upload_checks_extension_case_insensitively():
    assert is_allowed_upload("cover.PNG", {"png", "jpg"})
    assert not is_allowed_upload("cover.exe", {"png", "jpg"})


def test_is_allowed_upload_allows_allowed_extension_with_leading_dot():
    assert is_allowed_upload("cover.PNG", {".png"})


def test_is_allowed_upload_rejects_missing_extension_even_if_allowed_set_contains_empty_value():
    assert not is_allowed_upload("README", {""})
    assert not is_allowed_upload("README", {"."})


def test_is_allowed_upload_rejects_hidden_file_without_regular_extension():
    assert not is_allowed_upload(".env", {"env"})


def test_normalize_filename_strips_path_segments():
    assert normalize_filename("../config/users.json") == "users.json"
    assert normalize_filename(r"..\config\users.json") == "users.json"


def test_normalize_filename_preserves_safe_unicode_names():
    assert normalize_filename("长生俑 cover.png") == "长生俑 cover.png"


def test_normalize_filename_avoids_windows_reserved_names():
    assert normalize_filename("CON.png") == "_CON.png"


def test_build_public_asset_url_uses_url_prefix_not_filesystem_path():
    assert (
        build_public_asset_url("/assets/scenario_covers", "Camp One.png")
        == "/assets/scenario_covers/Camp%20One.png"
    )


def test_register_session_guard_rejects_expired_service_session_and_clears_session():
    class Manager:
        def is_session_current(self, user_id, token):
            return False

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["USER_MANAGER"] = Manager()
    register_session_guard(app)

    @app.route("/api/protected")
    def protected():
        return {"ok": True}

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session[SESSION_TOKEN_KEY] = "expired-token"

    response = client.get("/api/protected")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Session expired"
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_register_session_guard_allows_current_service_session():
    class Manager:
        def __init__(self):
            self.calls = []

        def is_session_current(self, user_id, token):
            self.calls.append((user_id, token))
            return True

    manager = Manager()
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["USER_MANAGER"] = manager
    register_session_guard(app)

    @app.route("/api/protected")
    def protected():
        return {"ok": True}

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session[SESSION_TOKEN_KEY] = "current-token"

    response = client.get("/api/protected")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert manager.calls == [(1, "current-token")]


def test_register_session_guard_keeps_legacy_active_session_registry_path():
    class Manager:
        pass

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["USER_MANAGER"] = Manager()
    app.config[ACTIVE_SESSION_REGISTRY_KEY] = {"1": "current-token"}
    register_session_guard(app)

    @app.route("/api/protected")
    def protected():
        return {"ok": True}

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session[SESSION_TOKEN_KEY] = "stale-token"

    response = client.get("/api/protected")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Session expired"
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_require_permission_rejects_expired_service_session_and_clears_session():
    class Manager:
        def __init__(self):
            self.permission_checked = False

        def is_session_current(self, user_id, token):
            return False

        def check_permission(self, user_id, required_role):
            self.permission_checked = True
            return True

    manager = Manager()
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["USER_MANAGER"] = manager

    @app.route("/admin")
    @require_permission("ADMIN")
    def protected():
        return {"ok": True}

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session[SESSION_TOKEN_KEY] = "expired-token"

    response = client.get("/admin")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Session expired"
    assert manager.permission_checked is False
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_require_permission_allows_current_service_session():
    class Manager:
        def __init__(self):
            self.session_calls = []
            self.permission_calls = []

        def is_session_current(self, user_id, token):
            self.session_calls.append((user_id, token))
            return True

        def check_permission(self, user_id, required_role):
            self.permission_calls.append((user_id, required_role))
            return True

    manager = Manager()
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["USER_MANAGER"] = manager

    @app.route("/admin")
    @require_permission("ADMIN")
    def protected():
        return {"ok": True}

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session[SESSION_TOKEN_KEY] = "current-token"

    response = client.get("/admin")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert manager.session_calls == [(1, "current-token")]
    assert manager.permission_calls == [(1, "ADMIN")]
