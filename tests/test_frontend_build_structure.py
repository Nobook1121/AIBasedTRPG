from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "frontend" / "dist" / "index.html"
STYLE_CSS = PROJECT_ROOT / "js" / "react" / "main.css"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build-frontend.mjs"
INDEX_MANIFEST = PROJECT_ROOT / "frontend" / "src" / "index" / "index.parts.json"
CHAT_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "chat.html"
SCENARIO_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "scenario.html"
ROOMS_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "rooms.html"
COOKIE_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "cookie-consent.html"
CHAT_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "chat.ts"
COOKIE_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "cookie-consent.ts"
SCENARIO_VIEW_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "views" / "ScenarioView.ts"
ROOMS_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "rooms.ts"
CHARACTER_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "character-sheet.ts"
REACT_ENTRY = PROJECT_ROOT / "frontend" / "src" / "react" / "main.tsx"
REACT_HOME = PROJECT_ROOT / "frontend" / "src" / "react" / "home" / "HomeChat.tsx"
REACT_SIDEBAR = PROJECT_ROOT / "frontend" / "src" / "react" / "shell" / "Sidebar.tsx"
REACT_SIDEBAR_CSS = PROJECT_ROOT / "frontend" / "src" / "react" / "shell" / "sidebar.css"
REACT_APP_CSS = PROJECT_ROOT / "frontend" / "src" / "react" / "app.css"
REACT_TSCONFIG = PROJECT_ROOT / "tsconfig.react.json"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_frontend_dist_html_and_react_css_are_built_from_source_fragments():
    assert BUILD_SCRIPT.exists()
    assert INDEX_MANIFEST.exists()
    assert REACT_APP_CSS.exists()

    script = _read(BUILD_SCRIPT)
    assert "index.parts.json" in script
    assert "frontend/dist/index.html" in script
    assert "generateTemplates" in script
    assert not (PROJECT_ROOT / "index.html").exists()
    assert not (PROJECT_ROOT / "style.css").exists()


def test_built_root_assets_do_not_contain_fragment_bom_characters():
    assert "\ufeff" not in _read(INDEX_HTML)
    assert "\ufeff" not in _read(STYLE_CSS)


def test_chat_uses_compiled_templates_before_chat_script_loads():
    html = _read(INDEX_HTML)
    source = _read(CHAT_TS)
    template_source = _read(CHAT_TEMPLATE)

    assert 'src="js/generated/templates.js"' in html
    assert html.index('src="js/generated/templates.js"') < html.index('src="js/chat.js"')
    assert html.index('src="js/generated/templates.js"') < html.index('src="js/cookie-consent.js"')
    assert '<template id="chat-message">' in template_source
    assert '<template id="chat-command-palette-item">' in template_source
    assert "window.TrpgTemplates.render(\"chat-message\"" in source
    assert "window.TrpgTemplates.render(\"chat-command-palette-item\"" in source
    assert "const messageHTML" not in source


def test_tool_scripts_are_loaded_from_data_tools():
    html = _read(INDEX_HTML)

    assert 'src="data/tools/diceTool.js"' in html
    assert 'src="data/tools/toolManager.js"' in html
    assert 'src="tools/diceTool.js"' not in html
    assert not (PROJECT_ROOT / "tools").exists()


def test_cookie_banner_uses_compiled_template():
    assert '<template id="cookie-consent-banner">' in _read(COOKIE_TEMPLATE)
    assert 'window.TrpgTemplates.render("cookie-consent-banner")' in _read(COOKIE_TS)


def test_scenario_and_room_views_use_compiled_templates():
    scenario_template = _read(SCENARIO_TEMPLATE)
    rooms_template = _read(ROOMS_TEMPLATE)
    scenario_source = _read(SCENARIO_VIEW_TS)
    rooms_source = _read(ROOMS_TS)

    assert '<template id="scenario-card">' in scenario_template
    assert '<template id="scenario-segment-editor">' in scenario_template
    assert '<template id="room-card">' in rooms_template
    assert '<template id="room-character-binding-table">' in rooms_template
    assert "<th>&#29609;&#23478;&#21517;</th>" in rooms_template
    assert "<th>&#32465;&#23450;&#35282;&#33394;&#21345;</th>" in rooms_template
    assert "<th>&#25151;&#38388;&#26435;&#38480;</th>" in rooms_template
    assert "&#26356;&#25913;&#35282;&#33394;&#21345;" in rooms_template
    assert "&#21024;&#38500;&#29609;&#23478;" in rooms_template
    assert "room-member-removed" in _read(PROJECT_ROOT / "frontend" / "src" / "styles" / "03-tools-settings-platform.css")
    assert 'window.TrpgTemplates.render("scenario-card"' in scenario_source
    assert 'window.TrpgTemplates.render("room-card"' in rooms_source
    assert 'window.TrpgTemplates.render("room-character-binding-table"' in rooms_source


def test_react_framework_is_bundled_before_application_scripts():
    html = _read(INDEX_HTML)
    package_source = _read(PROJECT_ROOT / "package.json")
    react_source = _read(REACT_ENTRY)

    assert 'id="react-runtime-root"' in html
    assert 'src="js/react/main.js"' in html
    assert html.index('src="js/react/main.js"') < html.index('src="js/main.js"')
    assert '"react"' in package_source
    assert '"react-dom"' in package_source
    assert '"esbuild"' in package_source
    assert '"build:react"' in package_source
    assert "--jsx=automatic" in package_source
    assert REACT_TSCONFIG.exists()
    assert 'createRoot' in react_source
    assert 'data-framework="react"' in react_source
    assert "alpinejs" not in package_source
    assert "vendor/alpine.js" not in html


def test_sidebar_shell_is_rendered_by_react_but_keeps_legacy_dom_contracts():
    html = _read(INDEX_HTML)
    index_source = _read(PROJECT_ROOT / "frontend" / "src" / "index" / "fragments" / "01-head-and-sidebar.html")
    react_entry = _read(REACT_ENTRY)
    sidebar_source = _read(REACT_SIDEBAR)
    sidebar_css = _read(REACT_SIDEBAR_CSS)
    app_css = _read(REACT_APP_CSS)

    assert 'id="react-sidebar-root"' in html
    assert 'id="react-sidebar-root"' in index_source
    assert 'id="sidebar"' not in index_source
    assert "flushSync" in react_entry
    assert 'document.getElementById("react-sidebar-root")' in react_entry
    assert 'id="sidebar"' in sidebar_source
    assert 'id="sidebarToggle"' in sidebar_source
    assert 'id="userInfo"' in sidebar_source
    assert 'tab: "home"' in sidebar_source
    assert "data-tab={tab}" in sidebar_source
    assert "#sidebar .nav-link" in sidebar_css
    assert '@import "./shell/sidebar.css";' in app_css


def test_home_chat_shell_is_rendered_by_react_with_legacy_dom_contracts():
    html = _read(INDEX_HTML)
    index_source = _read(PROJECT_ROOT / "frontend" / "src" / "index" / "fragments" / "02-main-tabs.html")
    react_entry = _read(REACT_ENTRY)
    home_source = _read(REACT_HOME)

    assert 'id="react-home-root"' in html
    assert 'id="react-home-root"' in index_source
    assert 'id="chatHistory"' not in index_source
    assert 'document.getElementById("react-home-root")' in react_entry
    assert "flushSync" in react_entry
    assert 'id="chatHistory"' in home_source
    assert 'id="chatInput"' in home_source
    assert 'id="sendButton"' in home_source
    assert 'id="saveStatusBar"' in home_source


def test_character_card_filters_and_limit_setting_are_present():
    index_source = _read(PROJECT_ROOT / "frontend" / "src" / "index" / "fragments" / "02-main-tabs.html")
    settings_source = _read(PROJECT_ROOT / "frontend" / "src" / "index" / "fragments" / "03-room-tools-auth-settings.html")
    character_source = _read(CHARACTER_TS)
    character_css = _read(PROJECT_ROOT / "frontend" / "src" / "styles" / "02-scenario-character.css")

    assert 'data-rank-filter="mine"' in index_source
    assert 'id="maxCardsPerUser"' in settings_source
    assert "maxCardsPerUser" in character_source
    assert "activeCharacterFilter" in character_source
    assert "currentUserCharacterCards" in character_source
    assert "occupiedByOther" not in character_source
    assert ".character-empty-filter" in character_css


def test_character_admin_player_binding_editor_is_assignable():
    modal_source = _read(PROJECT_ROOT / "frontend" / "src" / "index" / "fragments" / "04-editor-modals.html")
    character_source = _read(CHARACTER_TS)

    bound_input = '<input type="text" class="form-control" id="characterBoundPlayer" maxlength="80" list="characterPlayerOptions">'
    assert bound_input in modal_source
    assert 'id="characterPlayerOptions"' in modal_source
    assert 'id="characterBoundPlayer" maxlength="80" readonly' not in modal_source
    assert "loadAssignableUsers" in character_source
    assert "setPlayerBindingInputValue(\"\")" in character_source
    assert "if (isCurrentUserElevated())" in character_source
    assert "assignableUsers.find" in character_source
    assert "existing?.playerId && existing.playerId !== PLAYER_UNBOUND_LABEL) return existing.playerId" not in character_source


def test_character_owner_display_uses_player_names_for_admin_views():
    character_source = _read(CHARACTER_TS)

    assert "function playerDisplayName" in character_source
    assert "playerDisplayName(card.playerId)" in character_source
    assert "绑定玩家 ${escapeHtml(card.playerId || PLAYER_UNBOUND_LABEL)}" not in character_source
    assert "? cards" in character_source
    assert ": currentUserCharacterCards()" in character_source


def test_chat_ai_thinking_state_is_broadcast_with_live_elapsed_time():
    chat_source = _read(CHAT_TS)

    assert "type?: \"ai_thinking_start\" | \"ai_thinking_end\"" in chat_source
    assert "aiRequestId" in chat_source
    assert "broadcastAIThinkingStart" in chat_source
    assert "broadcastAIThinkingEnd" in chat_source
    assert "startThinkingElapsedTimer" in chat_source
    assert "window.setInterval" in chat_source
    assert "updateThinkingElapsed" in chat_source
    assert "clearThinkingMessage" in chat_source
    assert "handleAIThinkingEvent" in chat_source
    assert "renderProcessingTime(\"kp\", elapsedSeconds" in chat_source
