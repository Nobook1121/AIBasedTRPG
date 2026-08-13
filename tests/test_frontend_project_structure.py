import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_browser_sources_live_under_app_directory():
    assert not (ROOT / "frontend/src/js").exists()
    assert (ROOT / "frontend/src/app/main.ts").is_file()
    assert (ROOT / "frontend/src/app/auth/api.ts").is_file()
    assert (ROOT / "frontend/src/app/controllers/ScenarioController.ts").is_file()


def test_frontend_source_tree_separates_types_and_build_artifacts():
    assert (ROOT / "frontend/src/types/global.d.ts").is_file()
    assert not (ROOT / "frontend/src/app/types.d.ts").exists()
    assert not (ROOT / "frontend/dist").exists()
    assert not (ROOT / "js").exists()
    assert not (ROOT / "data/tools").exists()


def test_frontend_compiler_reads_app_sources_and_writes_dist_public():
    tsconfig = json.loads((ROOT / "tsconfig.frontend.json").read_text(encoding="utf-8"))

    assert "frontend/src/app/**/*.ts" in tsconfig["include"]
    assert "frontend/src/js/**/*.ts" not in tsconfig["include"]
    assert tsconfig["compilerOptions"]["outDir"] == "dist/public"


def test_frontend_theme_tokens_are_loaded_before_component_styles():
    app_css = (ROOT / "frontend/src/react/app.css").read_text(encoding="utf-8")
    first_import = next(line for line in app_css.splitlines() if line.startswith("@import"))

    assert first_import == '@import "../styles/00-theme-tokens.css";'
    assert (ROOT / "frontend/src/styles/00-theme-tokens.css").is_file()


def test_frontend_theme_selector_exposes_cyber_theme():
    settings_fragment = (ROOT / "frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")

    assert '<option value="pattern_cyber_2">赛博档案</option>' in settings_fragment


def test_frontend_theme_manager_uses_canonical_body_theme_classes():
    config_manager = (ROOT / "frontend/src/app/config/ConfigManager.ts").read_text(encoding="utf-8")

    assert 'themeClassNames = ["theme-light", "theme-dark", "theme-cyber-2", "light-theme", "dark-theme"]' in config_manager
    assert 'document.body.classList.add("theme-cyber-2")' in config_manager


def test_frontend_sidebar_uses_theme_tokens_instead_of_bootstrap_color_utilities():
    sidebar = (ROOT / "frontend/src/react/shell/Sidebar.tsx").read_text(encoding="utf-8")

    assert "bg-dark" not in sidebar
    assert "text-white" not in sidebar


def test_login_checkboxes_use_auth_specific_rendering_and_no_focus_glow():
    settings_fragment = (ROOT / "frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    auth_css = (ROOT / "frontend/src/styles/04-auth-profile-overrides.css").read_text(encoding="utf-8")

    assert 'class="auth-check-input"' in settings_fragment
    assert ".auth-check-input:checked::after" in auth_css
    assert ".auth-check-input:focus" in auth_css
    assert "box-shadow: none;" in auth_css
    assert "transition: border-color 0.16s ease, background-color 0.16s ease, transform 0.16s ease;" in auth_css
    assert "inset: 50% auto auto 50%;" in auth_css
    assert "transform: translate(-50%, -58%) rotate(45deg);" in auth_css


def test_scenario_preview_long_text_wraps_in_preview_sections():
    scenario_css = (ROOT / "frontend/src/styles/02-scenario-character.css").read_text(encoding="utf-8")
    scenario_template = (ROOT / "frontend/src/templates/scenario.html").read_text(encoding="utf-8")

    assert ".scenario-preview" in scenario_css
    assert "overflow-wrap: anywhere;" in scenario_css
    assert "white-space: pre-wrap;" in scenario_css
    assert ".scenario-preview-segment" in scenario_css
    assert "margin: 0 0 8px;" in scenario_css
    assert 'class="scenario-preview-segment mb-3"' not in scenario_template
    assert 'class="scenario-preview-segment"' in scenario_template


def test_tools_tab_exposes_available_command_tools():
    settings_fragment = (ROOT / "frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    main_ts = (ROOT / "frontend/src/app/main.ts").read_text(encoding="utf-8")

    for tool_name in [
        "dice",
        "coc-check",
        "room-snapshot",
        "scenario-context",
        "character-cards",
        "memory",
        "character-record",
    ]:
        assert f'data-tool="{tool_name}"' in settings_fragment
        assert f'id="{tool_name}-tool-content"' in settings_fragment

    assert "initCommandToolPanels" in main_ts
    assert "submitCocCheck" in main_ts
    assert "submitScenarioContext" in main_ts
    assert "submitRememberFact" in main_ts


def test_main_tabs_have_decorated_page_headers():
    fragments = [
        (ROOT / "frontend/src/index/fragments/02-main-tabs.html").read_text(encoding="utf-8"),
        (ROOT / "frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8"),
    ]
    combined = "\n".join(fragments)

    for tab_id in ["chat", "save", "scenario", "characters", "tools", "settings"]:
        assert f'data-page-header="{tab_id}"' in combined
    assert "page-command-header" in combined


def test_dark_theme_text_tokens_are_less_luminous():
    tokens = (ROOT / "frontend/src/styles/00-theme-tokens.css").read_text(encoding="utf-8")

    assert "--theme-text-primary: #d7dde3;" in tokens
    assert "--theme-text-secondary: #b8c0ca;" in tokens
    assert "--theme-text-primary: #c7d8d1;" in tokens
    assert "--theme-text-secondary: #aebfb8;" in tokens


def test_settings_exposes_data_driven_permission_matrix():
    settings_fragment = (ROOT / "frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    tabs_ts = (ROOT / "frontend/src/app/tabs.ts").read_text(encoding="utf-8")
    styles = (ROOT / "frontend/src/styles/03-tools-settings-platform.css").read_text(encoding="utf-8")

    assert 'data-settings="permissions"' in settings_fragment
    assert 'id="permissions-settings-content"' in settings_fragment
    assert 'id="permissionMatrix"' in settings_fragment
    assert "/api/config/permissions" in tabs_ts
    assert "renderPermissionMatrix" in tabs_ts
    assert "savePermissionConfig" in tabs_ts
    assert "permission-node-card" in styles
