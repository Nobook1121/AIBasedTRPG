from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "index.html"
STYLE_CSS = PROJECT_ROOT / "style.css"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build-frontend.mjs"
INDEX_MANIFEST = PROJECT_ROOT / "frontend" / "src" / "index" / "index.parts.json"
STYLE_MANIFEST = PROJECT_ROOT / "frontend" / "src" / "styles" / "style.parts.json"
CHAT_TEMPLATE = PROJECT_ROOT / "frontend" / "src" / "templates" / "chat.html"
CHAT_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "chat.ts"


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
    assert '<template id="chat-message">' in template_source
    assert '<template id="chat-command-palette-item">' in template_source
    assert "window.TrpgTemplates.render(\"chat-message\"" in source
    assert "window.TrpgTemplates.render(\"chat-command-palette-item\"" in source
    assert "const messageHTML" not in source
