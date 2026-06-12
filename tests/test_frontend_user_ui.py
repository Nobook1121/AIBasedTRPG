from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "index.html"
STYLE_CSS = PROJECT_ROOT / "style.css"
AUTH_DIR = PROJECT_ROOT / "frontend" / "src" / "js" / "auth"
AUTH_LOGIN_JS = PROJECT_ROOT / "js" / "auth" / "login-view.js"
AUTH_USER_CARD_JS = PROJECT_ROOT / "js" / "auth" / "user-card.js"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_login_and_register_are_independent_views():
    source = _read(INDEX_HTML)

    assert 'id="login-view"' in source
    assert 'id="register-view"' in source
    assert 'id="auth-tabs"' not in source
    assert 'class="auth-tab' not in source


def test_register_contains_confirm_password_and_terms():
    source = _read(INDEX_HTML)

    assert 'id="registerConfirmPassword"' in source
    assert 'id="acceptTerms"' in source
    assert "服务条款" in source
    assert "隐私协议" in source


def test_user_card_and_profile_dialog_exist():
    source = _read(INDEX_HTML)

    assert 'id="user-card-popover"' in source
    assert 'id="edit-profile-dialog"' in source
    assert "编辑个人资料" in source
    assert "切换账户" in source
    assert 'data-profile-target="profile-account-info"' in source


def test_floating_placeholder_css_exists():
    source = _read(STYLE_CSS)

    assert ".auth-floating-field" in source
    assert ".auth-floating-label" in source
    assert "pointer-events: none" in source
    assert "transition:" in source


def test_old_auth_tabs_css_removed():
    source = _read(STYLE_CSS)

    assert ".auth-tabs" not in source
    assert ".auth-tab" not in source


def test_register_fields_have_spacing_css():
    source = _read(STYLE_CSS)

    assert ".register-form-fields" in source
    assert "gap:" in source


def test_auth_typescript_no_longer_uses_nocheck():
    for source_path in AUTH_DIR.glob("*.ts"):
        assert "@ts-nocheck" not in _read(source_path)


def test_auth_module_split_exists():
    assert (AUTH_DIR / "index.ts").exists()
    assert (AUTH_DIR / "api.ts").exists()
    assert (AUTH_DIR / "floating-field.ts").exists()
    assert (AUTH_DIR / "user-card.ts").exists()
    assert (AUTH_DIR / "profile-dialog.ts").exists()


def test_init_auth_prefills_before_binding_floating_fields():
    source = _read(AUTH_DIR / "index.ts")

    assert source.index("prefillRememberedUsername()") < source.index("bindFloatingFields()")


def test_auth_uses_split_entry_without_legacy_wrapper():
    source = _read(INDEX_HTML)

    assert 'src="js/auth/index.js"' in source
    assert 'src="js/auth.js"' not in source


def test_login_reconnects_socket_and_reloads_user_scoped_room():
    source = _read(AUTH_LOGIN_JS)

    assert "window.reconnectSocket?.()" in source
    assert "window.autoLoadLastRoom?.()" in source


def test_switch_account_clears_room_and_chat():
    source = _read(AUTH_USER_CARD_JS)

    assert "switchAccount" in source
    assert "window.clearCurrentRoom?.()" in source
    assert "window.clearChatMessages?.()" in source


def test_profile_save_uploads_avatar_with_form_data():
    source = _read(AUTH_DIR / "profile-dialog.ts")

    assert "new FormData()" in source
    assert 'formData.append("avatar"' in source
    assert 'TrpgApi.post<ApiResponse<CurrentUser>>("/api/auth/update", formData)' in source


def test_profile_sidebar_tabs_have_switch_handler():
    source = _read(AUTH_DIR / "profile-dialog.ts")

    assert "bindProfileNavigation" in source
    assert "[data-profile-target]" in source
    assert "scrollIntoView" in source


def test_user_card_uses_grouped_menu_and_presence_flyout():
    source = _read(INDEX_HTML)

    assert "user-card-menu-section" in source
    assert "presence-menu-item" in source
    assert "presence-submenu" in source
    assert 'aria-haspopup="menu"' in source
    assert "fa fa-user" in source
    assert "fa fa-chevron-right" in source


def test_profile_editor_is_scroll_page_with_nested_navigation():
    source = _read(INDEX_HTML)

    assert "profile-dialog-topbar" in source
    assert source.index("profile-dialog-topbar") < source.index("profile-settings-sidebar")
    assert source.index('id="close-settings-panel"') < source.index("profile-settings-sidebar")
    assert 'data-profile-target="profile-account-info"' in source
    assert 'data-profile-target="profile-password-management"' in source
    assert 'id="profile-account-info"' in source
    assert 'id="profile-password-management"' in source
    assert "profile-subnav" in source
    assert "profile-save-bar" in source
    assert 'id="open-password-dialog"' in source


def test_password_change_uses_dedicated_dialog():
    source = _read(INDEX_HTML)

    assert 'id="password-dialog"' in source
    assert 'id="changePasswordButton"' in source
    assert 'id="passwordCurrentPassword"' in source
    assert 'id="passwordNewPassword"' in source
    assert 'id="passwordConfirmPassword"' in source


def test_user_profile_ui_motion_styles_exist():
    source = _read(STYLE_CSS)

    assert ".profile-dialog-topbar" in source
    assert "grid-column: 1 / -1" in source
    assert ".presence-submenu" in source
    assert ".profile-settings-content" in source
    assert ".profile-save-bar" in source
    assert ".password-dialog" in source
    assert "transform:" in source


def test_sidebar_brand_scales_without_wrapping():
    source = _read(STYLE_CSS)

    assert ".sidebar-title" in source
    assert "white-space: nowrap" in source
    assert "clamp(" in source


def test_localization_keys_are_present_on_touched_user_ui():
    source = _read(INDEX_HTML)

    assert 'data-i18n="auth.login.title"' in source
    assert 'data-i18n="room.status.current_room"' in source
    assert 'data-i18n-placeholder="chat.placeholder.room_required"' in source
