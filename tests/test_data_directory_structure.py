from pathlib import Path

from trpg_server import settings
from trpg_server.app_factory import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_data_directories_are_grouped_under_data_root():
    assert settings.DATA_DIR == PROJECT_ROOT / "data"

    runtime_paths = [
        settings.SCENARIOS_DIR,
        settings.CHARACTERS_DIR,
        settings.SCENARIO_COVERS_DIR,
        settings.AVATARS_DIR,
        settings.AI_PLATFORM_ASSETS_DIR,
        settings.TOOLS_DIR,
        settings.ROOMS_DIR,
        settings.CONFIG_DIR,
        settings.USERS_DIR,
        settings.HISTORY_DIR,
        settings.LOGS_DIR,
    ]

    for path in runtime_paths:
        assert path.is_relative_to(settings.DATA_DIR)

    assert not (PROJECT_ROOT / "assets").exists()


def test_data_root_is_not_served_by_generic_static_route(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
            "LOGS_DIR": tmp_path / "logs",
        }
    )

    response = app.test_client().get("/data/users/users.sqlite3")

    assert response.status_code == 404


def test_public_asset_urls_are_backed_by_data_assets(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "USER_DATABASE_FILE": tmp_path / "users.sqlite3",
            "USERS_FILE": tmp_path / "users.json",
            "USER_IP_CONFIG_DIR": tmp_path / "ip_configs",
            "LOGS_DIR": tmp_path / "logs",
        }
    )
    client = app.test_client()

    assert client.get("/assets/avatars/default.jpg").status_code == 200
    assert client.get("/assets/scenario_covers/default_cover.png").status_code == 200
    assert client.get("/assets/aiplatform/deepseek.png").status_code == 200
    assert client.get("/data/tools/diceTool.js").status_code == 200
