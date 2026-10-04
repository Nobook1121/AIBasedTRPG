import logging

import requests
from flask import Blueprint, request, session

from trpg_server.ai_capabilities import chat_completions_endpoint
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, server_error, success_response
from trpg_server.scenario_ai import (
    clean_module_summary,
    extract_ai_response,
    load_enabled_platform,
    module_summary_user_prompt,
    select_model,
    summary_role,
)
from trpg_server.routes.scenarios import _can_use_permission, _require_login

bp = Blueprint("scenario_summary", __name__)
logger = logging.getLogger(__name__)


@bp.route("/api/scenarios/module-summary", methods=["POST"])
def summarize_scenario_module():
    try:
        login_error = _require_login()
        if login_error:
            return login_error
        if not (_can_use_permission("scenarios.edit") or _can_use_permission("scenarios.create")):
            return error_response("Permission denied", 403, "Permission denied")

        request_data = request.get_json(silent=True)
        if not isinstance(request_data, dict):
            return error_response("Invalid module summary data", 400)

        module = request_data.get("module")
        if not isinstance(module, dict):
            return error_response("Module data is required", 400)

        role = summary_role()
        selected_platform, platform_config = load_enabled_platform(role.get("provider"))
        if not platform_config:
            return error_response("No enabled AI platform", 400, "No enabled platform")

        api_key = platform_config.get("config", {}).get("api_key")
        base_url = chat_completions_endpoint(platform_config.get("config", {}).get("base_url"))
        if not base_url:
            return error_response("AI platform config is incomplete", 400, "Incomplete platform config")
        if not api_key and selected_platform == "lmstudio":
            api_key = "lm-studio"
        elif not api_key:
            return error_response("AI platform config is incomplete", 400, "Incomplete platform config")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        model = select_model(platform_config)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": str(role.get("prompt") or "")},
                {"role": "user", "content": module_summary_user_prompt(request_data.get("scenario_title"), module)},
            ],
            "max_tokens": 180,
            "temperature": 0.2,
            "top_p": 0.8,
        }
        try:
            timeout = int(platform_config.get("config", {}).get("timeout", 30))
        except (TypeError, ValueError):
            timeout = 30
        response = requests.post(base_url, headers=headers, json=payload, timeout=max(15, min(timeout, 60)))
        response_data = response.json()
        if not isinstance(response_data, dict):
            return error_response("AI 平台返回的数据格式无效", 502, "Response must be a JSON object")
        if response.status_code != 200:
            error_message = response_data.get("error", {}).get("message", f"API request failed: {response.status_code}")
            return error_response(None, response.status_code, error_message)

        summary, token_count = extract_ai_response(response_data)
        summary = clean_module_summary(summary)
        if not summary:
            return error_response("AI platform did not return a module summary", 500, "No summary")

        log_user_action(
            logger,
            user_action_text(session.get("username"), "生成了剧本模块摘要"),
            用户ID=session.get("user_id"),
            模块类型=str(module.get("module_type") or ""),
            模块标题=str(module.get("title") or ""),
            token_count=token_count,
        )
        return success_response(
            data={"summary": summary, "token_count": token_count, "role_id": role.get("id"), "model": model},
            message="Module summary generated successfully",
        )
    except requests.exceptions.Timeout:
        logger.warning("Scenario module summary request timed out")
        return error_response("AI 平台请求超时，请稍后重试", 504, "Request timeout")
    except requests.exceptions.ConnectionError:
        logger.warning("Scenario module summary connection failed")
        return error_response("无法连接 AI 平台，请检查网络或平台配置", 503, "Connection error")
    except requests.exceptions.RequestException as exc:
        logger.warning("Scenario module summary request failed: %s", exc)
        return error_response("AI 平台请求失败", 502, str(exc))
    except ValueError as exc:
        logger.warning("Scenario module summary returned invalid JSON: %s", exc)
        return error_response("AI 平台返回的数据格式无效", 502, str(exc))
    except Exception as exc:
        logger.exception("Failed to generate module summary")
        return server_error("Failed to generate module summary")