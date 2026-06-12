from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTH_LOGIN_JS = PROJECT_ROOT / "js" / "auth" / "login-view.js"
ROOMS_JS = PROJECT_ROOT / "js" / "rooms.js"
COOKIE_JS = PROJECT_ROOT / "js" / "cookie-consent.js"
INDEX_HTML = PROJECT_ROOT / "index.html"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_cookie_consent_script_is_loaded_before_auth_and_rooms():
    source = _read(INDEX_HTML)

    assert 'src="js/cookie-consent.js"' in source
    assert source.index('src="js/cookie-consent.js"') < source.index('src="js/auth/index.js"')
    assert source.index('src="js/cookie-consent.js"') < source.index('src="js/rooms.js"')


def test_cookie_consent_module_prompts_first_visit_and_exposes_helpers():
    source = _read(COOKIE_JS)

    assert "trpg_cookie_consent" in source
    assert "showCookieConsentBanner" in source
    assert "window.TrpgCookies" in source


def test_auth_uses_cookie_for_last_username_only():
    source = _read(AUTH_LOGIN_JS)

    assert 'TrpgCookies.set("trpg_last_username"' in source
    assert 'TrpgCookies.get("trpg_last_username")' in source
    assert "password" not in source.split('TrpgCookies.set("trpg_last_username"')[1].split(");")[0]


def test_auth_errors_are_localized_on_login_and_register():
    api_source = _read(PROJECT_ROOT / "js" / "auth" / "api.js")
    login_source = _read(AUTH_LOGIN_JS)
    register_source = _read(PROJECT_ROOT / "js" / "auth" / "register-view.js")

    assert "localizedAuthMessage" in login_source
    assert "localizedAuthMessage" in register_source
    assert "用户名或邮箱或密码错误" in api_source
    assert "用户名已存在" in api_source


def test_rooms_use_cookie_for_user_scoped_last_room():
    source = _read(ROOMS_JS)

    assert "TrpgCookies.set(getLastRoomStorageKey()" in source
    assert "TrpgCookies.get(getLastRoomStorageKey())" in source
