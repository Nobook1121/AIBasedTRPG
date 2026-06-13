from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "index.html"
STYLE_CSS = PROJECT_ROOT / "style.css"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build-frontend.mjs"
INDEX_MANIFEST = PROJECT_ROOT / "frontend" / "src" / "index" / "index.parts.json"
STYLE_MANIFEST = PROJECT_ROOT / "frontend" / "src" / "styles" / "style.parts.json"
CHAT_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "chat.html"
SCENARIO_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "scenario.html"
ROOMS_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "rooms.html"
COOKIE_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "cookie-consent.html"
CHAT_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "chat.ts"
COOKIE_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "cookie-consent.ts"
SCENARIO_VIEW_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "views" / "ScenarioView.ts"
ROOMS_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "rooms.ts"
REACT_ENTRY = PROJECT_ROOT / "frontend" / "src" / "react" / "main.tsx"
REACT_SIDEBAR = PROJECT_ROOT / "frontend" / "src" / "react" / "shell" / "Sidebar.tsx"
REACT_SIDEBAR_CSS = PROJECT_ROOT / "frontend" / "src" / "react" / "shell" / "sidebar.css"
REACT_TSCONFIG = PROJECT_ROOT / "tsconfig.react.json"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_root_html_and_css_are_built_from_source_fragments():
    assert BUILD_SCRIPT.exists()
    assert INDEX_MANIFEST.exists()
    assert STYLE_MANIFEST.exists()

    script = _read(BUILD_SCRIPT)
    assert "index.parts.json" in script
    assert "style.parts.json" in script
    assert "generateTemplates" in script


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
    assert '<template id="room-character-binding">' in rooms_template
    assert 'window.TrpgTemplates.render("scenario-card"' in scenario_source
    assert 'window.TrpgTemplates.render("room-card"' in rooms_source
    assert 'window.TrpgTemplates.render("room-character-binding"' in rooms_source


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
    style_manifest = _read(STYLE_MANIFEST)

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
    assert "../react/shell/sidebar.css" in style_manifest
