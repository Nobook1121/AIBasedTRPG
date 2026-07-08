import json
import logging
import re
import time

import requests
from flask import Blueprint, current_app, request, session

from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.context import build_agent_context
from trpg_server.agents.profiles import resolve_agent_profile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.tools import default_tool_registry
from trpg_server.agents.tools.room import get_room_snapshot
from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import load_roles, select_role_for_content
from trpg_server.settings import CONFIG_DIR, HISTORY_DIR, ROOMS_DIR, SCENARIOS_DIR

bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)
_HISTORY_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")
HISTORY_COMPACT_CHAR_THRESHOLD = 12000


def _timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _message_response(user_id, content, message, script_id=None):
    payload = {
        "user_id": user_id,
        "content": content,
        "timestamp": _timestamp(),
    }
    if script_id is not None:
        payload["script_id"] = script_id

    return success_response(payload, message)


def _get_ai_platform_dir():
    return current_app.config.get("AI_PLATFORM_DIR", CONFIG_DIR / "aiplatform")


def _get_config_dir():
    return current_app.config.get("CONFIG_DIR", CONFIG_DIR)


def _get_history_dir():
    return current_app.config.get("HISTORY_DIR", HISTORY_DIR)


def _get_kp_prompt_file():
    return current_app.config.get("KP_PROMPT_FILE", CONFIG_DIR / "roles" / "kp.md")


def _get_role_config_file():
    return current_app.config.get("ROLE_CONFIG_FILE", CONFIG_DIR / "roles" / "roles.json")


def _load_enabled_platform(provider_id=None):
    platform_dir = _get_ai_platform_dir()
    if not platform_dir.exists():
        logger.warning("AI platform config directory does not exist: %s", platform_dir)
        return None, None

    for path in platform_dir.glob("*.json"):
        if provider_id and path.stem != provider_id:
            continue
        try:
            config = read_json(path, default={})
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to read AI platform config: %s", path.name)
            continue

        if config.get("enabled", False):
            return path.stem, config

    return None, None


def _load_role_for_content(content):
    roles = load_roles(_get_role_config_file(), _get_kp_prompt_file(), _get_ai_platform_dir())
    return select_role_for_content(roles, content)


def _json_for_log(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _post_ai_request(base_url, headers):
    def requester(payload):
        logger.info("AI API request payload: %s", _json_for_log(payload))
        response = requests.post(base_url, headers=headers, json=payload, timeout=300)
        if not response.ok:
            raise RuntimeError(f"API request failed: {response.status_code}")
        response_data = response.json()
        logger.info("AI API response payload: %s", _json_for_log(response_data))
        return response_data

    return requester


def _load_kp_prompt():
    prompt_path = _get_kp_prompt_file()
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to load KP prompt file: {prompt_path}") from exc

    content_lines = [
        line for line in content.splitlines() if not line.startswith("#") and line.strip()
    ]
    if content_lines:
        return "\n".join(content_lines)

    return "你是KP（守密人），负责主持TRPG游戏，引导玩家进行游戏。"


def _safe_history_part(value):
    text = str(value or "unknown").strip() or "unknown"
    return _HISTORY_SAFE_RE.sub("_", text)[:120]


def _history_filename(user_id, room_id=None, agent_id="kp"):
    safe_agent = _safe_history_part(agent_id)
    if room_id:
        return f"room-{_safe_history_part(room_id)}-{safe_agent}.json"
    return f"user-{_safe_history_part(user_id)}-{safe_agent}.json"


def _load_history(user_id, room_id=None, agent_id="kp"):
    history_file = _get_history_dir() / _history_filename(user_id, room_id, agent_id)
    return history_file, read_json(history_file, default=[])


def _speaker_for_user(room_info, user_id):
    for member in room_info.get("members", []):
        if str(member.get("user_id")) != str(user_id):
            continue
        character = member.get("character_card") or member.get("character") or {}
        return {
            "user_id": member.get("user_id"),
            "username": member.get("username") or str(user_id),
            "character_name": character.get("name"),
        }
    return {"user_id": user_id, "username": str(user_id)}


def _format_user_content(content, speaker=None):
    if not speaker:
        return content

    parts = [f"speaker={speaker.get('username') or speaker.get('user_id')}"]
    character_name = speaker.get("character_name")
    if character_name:
        parts.append(f"character={character_name}")
    return f"[{'; '.join(parts)}]\n{content}"


def _is_compact_command(content):
    text = str(content or "").strip()
    if text.startswith("@KP"):
        text = text[3:].strip()
    return text.casefold() == "/compact"


def _strip_compact_command(content):
    lines = str(content or "").splitlines()
    kept = []
    requested = False
    for line in lines:
        if line.strip().casefold() == "/compact":
            requested = True
            continue
        kept.append(line)
    return "\n".join(kept).strip(), requested


def _history_needs_compaction(history, threshold=HISTORY_COMPACT_CHAR_THRESHOLD):
    return sum(len(str(item.get("content") or "")) for item in history) > threshold


def _compact_history_entries(summary):
    return [{"role": "system", "content": f"历史压缩摘要：\n{summary.strip()}", "compact": True}]


def _compact_history_with_ai(requester, model, history):
    if not history:
        return []

    payload = {
        "model": model,
        "max_tokens": 1200,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "压缩TRPG房间历史。保留当前场景、关键事实、NPC状态、"
                    "每位玩家/调查员行动、未解决线索、检定结果。不要编造。"
                ),
            },
            {"role": "user", "content": _json_for_log(history)},
        ],
    }
    summary, _token_count = _extract_ai_response(requester(payload))
    if not summary.strip():
        raise RuntimeError("AI platform did not return a compact summary")
    return _compact_history_entries(summary)


def _select_model(platform_config):
    models = platform_config.get("models", [])
    if not models:
        return "local-model"

    model = next((item for item in models if item.get("enabled", True)), models[0])
    return model.get("id", "local-model")


def _compact_character_card(character_card):
    if not isinstance(character_card, dict):
        return None

    compact = {}
    for key in ("id", "name", "occupation", "age", "gender", "sex"):
        value = character_card.get(key)
        if value not in (None, ""):
            compact[key] = value
    return compact or None


def _compact_character_state(character_state):
    if not isinstance(character_state, dict):
        return None

    compact = {}
    for key in ("max_hp", "current_hp", "max_san", "current_san"):
        value = character_state.get(key)
        if value is not None:
            compact[key] = value
    return compact or None


def _count_list_items(value):
    return len(value) if isinstance(value, list) else 0


def _compact_room_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return {}

    scenario = snapshot.get("scenario")
    if isinstance(scenario, dict):
        available_sections = scenario.get("available_sections")
        if not isinstance(available_sections, dict):
            available_sections = {}
            for key in ("scenes", "locations", "npcs", "clues", "endings"):
                count = _count_list_items(scenario.get(key))
                if count:
                    available_sections[key] = count
        compact_scenario = {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description"),
            "found": scenario.get("found"),
            "available_sections": available_sections,
        }
    else:
        compact_scenario = scenario

    members = []
    for member in snapshot.get("members") or []:
        if not isinstance(member, dict):
            continue
        compact_member = {
            "user_id": member.get("user_id"),
            "username": member.get("username"),
            "active": member.get("active"),
        }
        character_card = _compact_character_card(member.get("character_card") or member.get("character"))
        if character_card:
            compact_member["character"] = character_card
        character_state = _compact_character_state(member.get("character_state"))
        if character_state:
            compact_member["character_state"] = character_state
        members.append(compact_member)

    return {
        "room": snapshot.get("room"),
        "scenario": compact_scenario,
        "members": members,
        "memory": snapshot.get("memory"),
    }


def _room_snapshot_system_message(snapshot):
    compact_snapshot = _compact_room_snapshot(snapshot)
    return (
        "当前房间资料由 function `room.get_room_snapshot` 读取。"
        "这是本次回复必须优先采用的当前房间、绑定剧本和玩家角色卡上下文；"
        "不得沿用其他房间的剧本、角色或记忆。\n"
        "自动注入的上下文已精简，不包含完整场景正文、角色卡技能或属性。"
        "需要详细剧本、角色卡技能或属性时，必须调用相应 room function。\n"
        f"{_json_for_log(compact_snapshot)}"
    )


def _build_messages(system_prompt, history, content, room_snapshot_message=None):
    messages = [{"role": "system", "content": system_prompt}]
    if room_snapshot_message:
        messages.append({"role": "system", "content": room_snapshot_message})
    for item in history:
        item_content = item["content"]
        if item.get("role") == "user":
            item_content = _format_user_content(item_content, item.get("speaker"))
        messages.append({"role": item["role"], "content": item_content})
    messages.append({"role": "user", "content": content})
    return messages


def _extract_ai_response(response_data):
    ai_response = ""
    choices = response_data.get("choices", [])
    if choices:
        choice = choices[0]
        if "message" in choice and "content" in choice["message"]:
            ai_response = choice["message"]["content"]
        elif "delta" in choice and "content" in choice["delta"]:
            ai_response = choice["delta"]["content"]

    token_count = None
    usage = response_data.get("usage")
    if usage:
        if "total_tokens" in usage:
            token_count = usage["total_tokens"]
        elif "completion_tokens" in usage and "prompt_tokens" in usage:
            token_count = usage["completion_tokens"] + usage["prompt_tokens"]

    return ai_response, token_count


@bp.route("/api/chat", methods=["POST"])
def chat():
    try:
        message_data = request.get_json(silent=True)
        if not message_data:
            return error_response("Please provide message data", 400, "No data")

        user_id = message_data.get("user_id", "unknown")
        content = message_data.get("content", "")
        role_config = _load_role_for_content(content)
        agent_profile = resolve_agent_profile(role_config, _get_kp_prompt_file())
        selected_platform, platform_config = _load_enabled_platform(agent_profile.provider)
        if not platform_config:
            return error_response(
                "No enabled AI platform",
                400,
                "No enabled platform",
            )

        api_key = platform_config.get("config", {}).get("api_key")
        base_url = platform_config.get("config", {}).get("base_url")
        if not base_url:
            return error_response(
                "AI platform config is incomplete",
                400,
                "Incomplete platform config",
            )

        if not api_key and selected_platform == "lmstudio":
            api_key = "lm-studio"
        elif not api_key:
            return error_response(
                "AI platform config is incomplete",
                400,
                "Incomplete platform config",
            )

        room_id = message_data.get("room_id")
        agent_context = build_agent_context(
            room_id=room_id,
            rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
            scenarios_dir=current_app.config.get("SCENARIOS_DIR", SCENARIOS_DIR),
            user_id=user_id,
            agent_id=agent_profile.id,
        )
        room_snapshot_message = None
        if room_id:
            room_snapshot_message = _room_snapshot_system_message(get_room_snapshot({}, agent_context))

        runtime_config = load_ai_runtime_config(_get_config_dir())
        model = _select_model(platform_config)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        requester = _post_ai_request(base_url, headers)
        history_file, history = _load_history(user_id, room_id=room_id, agent_id=agent_profile.id)

        if _is_compact_command(content):
            if history:
                history = _compact_history_with_ai(requester, model, history)
                write_json_atomic(history_file, history)
                response_text = "历史已压缩。"
            else:
                response_text = "当前没有可压缩的历史。"
            return success_response(message=None, content=response_text, token_count=None)

        if _history_needs_compaction(history):
            try:
                history = _compact_history_with_ai(requester, model, history)
                write_json_atomic(history_file, history)
            except Exception:
                logger.exception("Failed to compact chat history automatically")

        speaker = _speaker_for_user(agent_context.room_info(), user_id) if room_id else None
        user_content = _format_user_content(content, speaker)
        system_prompt = agent_profile.prompt or _load_kp_prompt()
        if room_id:
            system_prompt = f"{system_prompt}\n- 需压缩历史时，单独输出 /compact。"
        request_data = {
            "messages": _build_messages(
                system_prompt,
                history,
                user_content,
                room_snapshot_message=room_snapshot_message,
            ),
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        if runtime_config.stream_output:
            request_data["stream"] = False

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "发起了 AI 对话"),
            用户ID=session.get("user_id") or user_id,
            角色=role_config.get("id"),
            平台=selected_platform,
            模型=request_data["model"],
            内容长度=len(content),
        )
        result = run_agent_completion(
            requester=requester,
            base_payload=request_data,
            profile=agent_profile,
            registry=default_tool_registry(),
            context=agent_context,
        )
        if result.error:
            return error_response("AI agent request failed", 500, result.error)

        ai_response, compact_requested_by_ai = _strip_compact_command(result.content)
        token_count = result.token_count
        if not ai_response and compact_requested_by_ai:
            ai_response = "历史已压缩。"
        if not ai_response:
            return error_response(
                "AI platform did not return a response",
                400,
                "No response",
            )
        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "收到了 AI 对话回复"),
            用户ID=session.get("user_id") or user_id,
            平台=selected_platform,
            模型=request_data["model"],
            回复长度=len(ai_response),
            Token数=token_count,
        )

        user_history_item = {"role": "user", "content": content}
        if speaker:
            user_history_item["speaker"] = speaker
        history.extend([user_history_item, {"role": "assistant", "content": ai_response}])
        if compact_requested_by_ai:
            try:
                history = _compact_history_with_ai(requester, model, history)
                write_json_atomic(history_file, history)
            except Exception:
                logger.exception("Failed to compact chat history after AI request")
                write_json_atomic(history_file, history[-20:])
        else:
            write_json_atomic(history_file, history[-20:])

        return success_response(
            message=None,
            content=ai_response,
            token_count=token_count,
        )
    except requests.exceptions.Timeout:
        return error_response("AI platform request timeout", 504, "Request timeout")
    except requests.exceptions.ConnectionError:
        return error_response("Cannot connect to AI platform", 503, "Connection error")
    except json.JSONDecodeError as exc:
        logger.exception("Failed to parse AI platform response")
        return error_response("Failed to parse AI platform response", 500, str(exc))
    except Exception as exc:
        logger.exception("Chat request failed")
        return error_response("Chat request failed", 500, str(exc))


@bp.route("/api/messages", methods=["POST"])
def send_home_message():
    try:
        message_data = request.get_json(silent=True)
        if not message_data:
            return error_response("Please provide message data", 400, "No data")

        user_id = message_data.get("user_id", "unknown")
        message_content = message_data.get("content", "")
        if not message_content:
            return error_response(
                "Please provide message content",
                400,
                "No message content",
            )

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "发送了主页对话"),
            用户ID=session.get("user_id") or user_id,
            内容长度=len(message_content),
        )
        return _message_response(user_id, message_content, "Message sent successfully")
    except Exception as exc:
        logger.exception("Failed to send home message")
        return error_response("Failed to send message", 500, str(exc))


@bp.route("/api/scenarios/<int:script_id>/messages", methods=["POST"])
def send_message(script_id):
    try:
        message_data = request.get_json(silent=True)
        if not message_data:
            return error_response("Please provide message data", 400, "No data")

        user_id = message_data.get("user_id", "unknown")
        message_content = message_data.get("content", "")
        if not message_content:
            return error_response(
                "Please provide message content",
                400,
                "No message content",
            )

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "发送了剧本对话"),
            用户ID=session.get("user_id") or user_id,
            剧本ID=script_id,
            内容长度=len(message_content),
        )
        return _message_response(
            user_id,
            message_content,
            "Scenario message sent successfully",
            script_id=script_id,
        )
    except Exception as exc:
        logger.exception("Failed to send scenario message: %s", script_id)
        return error_response("Failed to send scenario message", 500, str(exc))
