"""首次部署引导（onboarding）接口。

这些接口只在系统还没有任何 OWNER 账号时可用，用于让自托管用户在网页上完成
初始配置：填写 AI API、为网站命名、记录域名、创建 owner 账号。一旦存在 OWNER，
所有写接口都会返回 403，避免他人接管已经部署好的实例。
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import timedelta

import requests
from flask import Blueprint, current_app, request, session

from trpg_server.ai_platform_config import load_platform_config, save_platform_config
from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import load_roles
from trpg_server.security import CSRF_SESSION_KEY, SESSION_TOKEN_KEY, safe_join
from trpg_server.settings import AI_PLATFORM_SECRET_DIR, CONFIG_DIR, SITE_CONFIG_FILE

bp = Blueprint("setup", __name__)
logger = logging.getLogger(__name__)

_PLATFORM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_MAX_SITE_NAME_LENGTH = 64
_MAX_DOMAIN_LENGTH = 253


def _get_config_dir():
    return current_app.config.get("CONFIG_DIR", CONFIG_DIR)


def _get_ai_platform_dir():
    return current_app.config.get("AI_PLATFORM_DIR", _get_config_dir() / "aiplatform")


def _get_ai_platform_secret_dir():
    return current_app.config.get("AI_PLATFORM_SECRET_DIR", AI_PLATFORM_SECRET_DIR)


def _get_user_manager():
    from trpg_server.users.manager import user_manager

    return current_app.config.get("USER_MANAGER", user_manager)


def _get_site_config_file():
    return current_app.config.get("SITE_CONFIG_FILE", SITE_CONFIG_FILE)


def _read_site_config() -> dict:
    config = read_json(_get_site_config_file(), default={})
    return config if isinstance(config, dict) else {}


def _owner_exists(manager) -> bool:
    try:
        users = manager.get_all_users()
    except Exception:
        logger.exception("Failed to list users while checking setup state")
        return True
    return any(str(user.get("role")) == "OWNER" for user in users)


def _setup_locked_response():
    return error_response("Setup already completed", 403, "Setup already completed")


@bp.route("/api/setup/status", methods=["GET"])
def setup_status():
    try:
        owner_exists = _owner_exists(_get_user_manager())
        site_config = _read_site_config()
        dismissed = bool(site_config.get("setup_dismissed"))
        return success_response(
            {
                "setup_required": not owner_exists and not dismissed,
                "owner_exists": owner_exists,
                "setup_dismissed": dismissed,
                "site_name": site_config.get("name", ""),
                "site_domain": site_config.get("domain", ""),
            }
        )
    except Exception as exc:
        logger.exception("Failed to determine setup status")
        return error_response("Failed to determine setup status", 500, str(exc))


@bp.route("/api/setup/dismiss", methods=["POST"])
def dismiss_setup():
    """记录用户已跳过引导，之后不再自动弹出。仅在系统尚无 OWNER 时可用。"""
    try:
        if _owner_exists(_get_user_manager()):
            return _setup_locked_response()

        site_config = _read_site_config()
        site_config["setup_dismissed"] = True
        write_json_atomic(_get_site_config_file(), site_config)

        logger.info("Setup wizard dismissed")
        return success_response({"setup_dismissed": True})
    except Exception as exc:
        logger.exception("Failed to dismiss setup")
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/setup/site", methods=["POST"])
def save_site_config():
    try:
        if _owner_exists(_get_user_manager()):
            return _setup_locked_response()

        config_data = request.get_json(silent=True) or {}
        name = str(config_data.get("name") or "").strip()
        domain = str(config_data.get("domain") or "").strip()
        if not name:
            return error_response("Site name is required", 400, "Site name is required")
        if len(name) > _MAX_SITE_NAME_LENGTH:
            return error_response("Site name is too long", 400, "Site name is too long")
        if len(domain) > _MAX_DOMAIN_LENGTH:
            return error_response("Domain is too long", 400, "Domain is too long")

        site_config = _read_site_config()
        site_config["name"] = name
        site_config["domain"] = domain
        write_json_atomic(_get_site_config_file(), site_config)

        logger.info("Setup site config saved name=%s domain=%s", name, domain)
        return success_response({"name": name, "domain": domain})
    except Exception as exc:
        logger.exception("Failed to save site config")
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/setup/ai", methods=["POST"])
def save_ai_platform():
    try:
        if _owner_exists(_get_user_manager()):
            return _setup_locked_response()

        config_data = request.get_json(silent=True) or {}
        platform = str(config_data.get("platform") or "").strip()
        base_url = str(config_data.get("base_url") or "").strip()
        api_key = str(config_data.get("api_key") or "").strip()
        model_id = str(config_data.get("model") or "").strip()
        model_name = str(config_data.get("model_name") or "").strip()
        timeout = config_data.get("timeout")

        if not base_url or not model_id:
            return error_response("Base URL and model are required", 400, "Incomplete AI config")
        if not _PLATFORM_ID_RE.fullmatch(platform):
            return error_response("Invalid platform id", 400, "Invalid platform id")

        platform_dir = _get_ai_platform_dir()
        platform_dir.mkdir(parents=True, exist_ok=True)
        config_path = safe_join(platform_dir, f"{platform}.json")
        secret_path = safe_join(_get_ai_platform_secret_dir(), f"{platform}.json")

        existing = load_platform_config(config_path, secret_path) if config_path.exists() else {}
        config = existing if isinstance(existing, dict) else {}
        config["platform"] = platform
        config.setdefault("name", platform)
        config.setdefault("description", "")
        config.setdefault("icon", "")
        config["enabled"] = True
        config.setdefault("auth_method", "api_key")
        config.setdefault("version", "1.0.0")

        platform_config = config.get("config") if isinstance(config.get("config"), dict) else {}
        platform_config["base_url"] = base_url
        platform_config.setdefault("headers", {"Content-Type": "application/json"})
        if isinstance(timeout, (int, float)) and timeout > 0:
            platform_config["timeout"] = int(timeout)
        else:
            platform_config.setdefault("timeout", 60)
        if api_key:
            platform_config["api_key"] = api_key
        config["config"] = platform_config

        config["models"] = _upsert_model(config.get("models"), model_id, model_name)
        save_platform_config(config_path, secret_path, config)
        _repoint_roles_provider(platform)

        log_user_action(
            logger,
            "完成引导：配置了 AI 平台",
            平台=platform,
            BaseURL=base_url,
            模型=model_id,
        )
        return success_response({"platform": platform, "model": model_id})
    except Exception as exc:
        logger.exception("Failed to save AI platform during setup")
        return error_response(f"Save failed: {exc}", 500)


@bp.route("/api/setup/ai/test", methods=["POST"])
def test_ai_platform():
    try:
        if _owner_exists(_get_user_manager()):
            return _setup_locked_response()

        test_data = request.get_json(silent=True) or {}
        base_url = str(test_data.get("base_url") or "").strip()
        api_key = str(test_data.get("api_key") or "").strip()
        model_id = str(test_data.get("model") or "").strip()
        platform = str(test_data.get("platform") or "").strip()

        if not base_url or not model_id:
            return error_response("Base URL and model are required", 400, "Incomplete AI config")
        if not api_key and platform == "lmstudio":
            api_key = "lm-studio"

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 16,
            "temperature": 0,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        response = requests.post(base_url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            try:
                detail = response.json().get("error", {}).get("message", "")
            except ValueError:
                detail = response.text[:200]
            return error_response(None, response.status_code, detail or f"API request failed: {response.status_code}")

        return success_response(message=None, response=response.json())
    except Exception as exc:
        logger.exception("Failed to test AI platform during setup")
        return error_response(None, 500, str(exc))


@bp.route("/api/setup/owner", methods=["POST"])
def create_owner():
    try:
        manager = _get_user_manager()
        if _owner_exists(manager):
            return _setup_locked_response()

        user_data = request.get_json(silent=True) or {}
        username = str(user_data.get("username") or "").strip()
        email = str(user_data.get("email") or "").strip()
        password = user_data.get("password") or ""
        confirm_password = user_data.get("confirm_password") or ""

        if not username or not email or not password:
            return error_response("Please provide username, password, and email", 400, "Incomplete data")
        if password != confirm_password:
            return error_response("Passwords do not match", 400, "Passwords do not match")

        ip_address = request.remote_addr
        result = manager.register(
            username,
            password,
            email,
            terms_accepted=True,
            ip_address=ip_address,
        )
        success, message, user = result[0], result[1], result[2]
        if not success or not user:
            return error_response(message, 400, message)

        user_id = int(user["id"])
        role_success, role_message = manager.update_user_role(user_id, "OWNER")
        if not role_success:
            return error_response(role_message, 500, role_message)

        _start_owner_session(manager, username, password, ip_address)

        log_user_action(
            logger,
            user_action_text(username, "完成引导并创建了 owner 账号"),
            用户ID=user_id,
            邮箱=email,
            IP=ip_address,
        )
        return success_response(
            {"user_id": user_id, "username": username, "email": email, "role": "OWNER"},
            status=201,
        )
    except Exception as exc:
        logger.exception("Failed to create owner account during setup")
        return error_response("Failed to create owner account", 500, str(exc))


def _upsert_model(models, model_id: str, model_name: str) -> list:
    entries = [item for item in models if isinstance(item, dict)] if isinstance(models, list) else []
    for model in entries:
        if str(model.get("id")) == model_id:
            model["enabled"] = True
            if model_name:
                model["name"] = model_name
            return entries
    entries.insert(
        0,
        {
            "id": model_id,
            "name": model_name or model_id,
            "description": "",
            "enabled": True,
            "params": {
                "context_window": 8192,
                "temperature": 0.7,
                "top_p": 0.95,
                "max_tokens": 4096,
            },
        },
    )
    return entries


def _repoint_roles_provider(platform: str) -> None:
    """让 KP 等角色使用刚配置的平台，保证引导完成后 AI 即可用。"""
    config_dir = _get_config_dir()
    role_file = config_dir / "roles" / "roles.json"
    prompt_file = config_dir / "roles" / "kp.md"
    roles = load_roles(role_file, prompt_file, _get_ai_platform_dir())
    for role in roles:
        role["provider"] = platform
    write_json_atomic(role_file, {"roles": roles})


def _start_owner_session(manager, username: str, password: str, ip_address) -> None:
    login_result = manager.login(username, password, ip_address)
    if not login_result[0] or not login_result[2]:
        return
    user = login_result[2]
    token = login_result[3] if len(login_result) > 3 else None
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session[SESSION_TOKEN_KEY] = token or secrets.token_urlsafe(32)
    session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(days=7)