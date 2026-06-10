from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "index.html"
PLATFORM_UI_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "platform-ui.ts"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_frontend_config_managers_load_from_js_config_directory():
    html = _read(INDEX_HTML)

    assert 'src="js/config/TestRequestConfig.js"' in html
    assert 'src="js/config/ConfigManager.js"' in html
    assert 'src="js/config/AIPlatformManager.js"' in html
    assert 'src="config/TestRequestConfig.js"' not in html
    assert 'src="config/ConfigManager.js"' not in html
    assert 'src="config/AIPlatformManager.js"' not in html


def test_config_directory_does_not_contain_frontend_manager_scripts():
    assert not (PROJECT_ROOT / "config" / "TestRequestConfig.js").exists()
    assert not (PROJECT_ROOT / "config" / "ConfigManager.js").exists()
    assert not (PROJECT_ROOT / "config" / "AIPlatformManager.js").exists()


def test_ai_model_request_templates_use_json_files():
    assert (PROJECT_ROOT / "config" / "aiplatform" / "default-request.json").exists()
    assert not (PROJECT_ROOT / "config" / "aiplatform" / "default.js").exists()


def test_platform_ui_uses_json_model_request_config_files():
    source = _read(PLATFORM_UI_TS)

    assert "config/aiplatform/default-request.json" in source
    assert "config/aimodel/${platform}/${modelId}.json" in source
    assert "config/aiplatform/default.js" not in source
    assert "config/aimodel/${platform}/${modelId}.js`" not in source


def test_model_settings_include_role_config_and_provider_title():
    html = _read(INDEX_HTML)
    source = _read(PLATFORM_UI_TS)

    assert "角色配置" in html
    assert "大模型提供商" in html
    assert 'id="roleConfigList"' in html
    assert "/api/config/roles" in source
    assert "bindRoleConfigSettings" in source
    assert "renderRoleConfigCards" in source
