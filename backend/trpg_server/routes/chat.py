import json
import logging
import re
import time

import requests
from flask import Blueprint, current_app, request, session

from trpg_server.ai_platform_config import load_platform_config
from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.context import build_agent_context
from trpg_server.agents.profiles import resolve_agent_profile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.structured_output import apply_state_updates, parse_kp_response, validate_state_updates
from trpg_server.agents.telemetry import build_provider_cache_key, calculate_cache_hit_rate, record_ai_usage
from trpg_server.agents.prompt_builder import build_prompt_layers
from trpg_server.agents.tools import default_tool_registry
from trpg_server.agents.tools.room import get_room_snapshot
from trpg_server.agents.memory import remember_room_fact
from trpg_server.agents.room_state import append_room_event, project_room_state
from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import load_roles, provider_small_model_config, select_role_for_content
from trpg_server.settings import (
    AI_PLATFORM_SECRET_DIR,
    CONFIG_DIR,
    HISTORY_DIR,
    ROOMS_DIR,
    SCENARIOS_DIR,
    LOGS_DIR,
)

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


def _get_ai_platform_secret_dir():
    return current_app.config.get("AI_PLATFORM_SECRET_DIR", AI_PLATFORM_SECRET_DIR)


def _get_config_dir():
    return current_app.config.get("CONFIG_DIR", CONFIG_DIR)


def _get_history_dir():
    return current_app.config.get("HISTORY_DIR", HISTORY_DIR)


def _get_kp_prompt_file():
    return current_app.config.get("KP_PROMPT_FILE", CONFIG_DIR / "roles" / "kp.md")


def _get_debug_kp_prompt_file():
    return current_app.config.get("DEBUG_KP_PROMPT_FILE", _get_config_dir() / "roles" / "debug-kp.md")


def _get_role_config_file():
    return current_app.config.get("ROLE_CONFIG_FILE", CONFIG_DIR / "roles" / "roles.json")


def _load_enabled_platform(provider_id=None):
    platform_dir = _get_ai_platform_dir()
    secret_dir = _get_ai_platform_secret_dir()
    if not platform_dir.exists():
        logger.warning("AI platform config directory does not exist: %s", platform_dir)
        return None, None

    for path in platform_dir.glob("*.json"):
        if provider_id and path.stem != provider_id:
            continue
        try:
            secret_path = secret_dir / path.name
            config = load_platform_config(path, secret_path)
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
            try:
                detail = response.json()
                detail = detail.get("error", detail) if isinstance(detail, dict) else detail
            except (ValueError, requests.exceptions.JSONDecodeError):
                detail = str(getattr(response, "text", ""))[:500]
            raise RuntimeError(f"AI 平台请求失败（HTTP {response.status_code}）：{detail}")
        response_data = response.json()
        if not isinstance(response_data, dict):
            raise RuntimeError("AI 平台返回的数据格式无效：响应必须是对象")
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

    return "你是KP（守秘人），负责主持以克苏鲁的呼唤第七版规则为基础的桌上角色扮演游戏。"


def _load_debug_kp_prompt():
    prompt_path = _get_debug_kp_prompt_file()
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError:
        return (
            "你是用于调试工具调用的KP。只能使用已启用的房间资料和检定工具。\n"
            "需要检定时调用 check.roll_room_check，并在工具返回后复述检定摘要。"
        )

    content_lines = [line for line in content.splitlines() if not line.startswith("#") and line.strip()]
    return "\n".join(content_lines) or "你是用于调试工具调用的KP。"


def _safe_history_part(value):
    text = str(value or "unknown").strip() or "unknown"
    return _HISTORY_SAFE_RE.sub("_", text)[:120]


def _history_filename(user_id, room_id=None, agent_id="kp"):
    safe_agent = _safe_history_part(agent_id)
    if room_id:
        return f"room-{_safe_history_part(room_id)}-{safe_agent}.json"
    return f"user-{_safe_history_part(user_id)}-{safe_agent}.json"


def _room_session_id(room_id, agent_id="kp"):
    return f"room:{_safe_history_part(room_id)}:agent:{_safe_history_part(agent_id)}"


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


def _wrap_user_input(content):
    return "\n".join(
        [
            "---->USER_INPUT<----",
            str(content or ""),
            "---->END_USER_INPUT<----",
        ]
    )


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


def _request_allows_check(content):
    text = str(content or "").strip()
    if text.startswith("@KP"):
        text = text[3:].strip()
    return bool(re.search(r"(?:^|\s)(?:/check|检定|投骰|掷骰|侦察|侦查|观察|搜索|搜查|调查|检查)(?:\s|$)", text, re.IGNORECASE))


def _request_allows_manual_trigger(content):
    text = str(content or "").strip()
    if text.startswith("@KP"):
        text = text[3:].strip()
    return text.startswith("/trigger") or "手动触发" in text


def _request_allows_scene_transition(content):
    text = str(content or "").strip()
    if text.startswith("@KP"):
        text = text[3:].strip()
    if text.startswith("/scene"):
        return True
    if re.search(r"(?:不要|别|不想|无需)(?:进入|前往|来到|离开|跑到|去往|转场|切换场景)", text, re.IGNORECASE):
        return False
    return bool(re.search(r"(进入|前往|来到|离开|跑到|去往|转场|切换场景|go to|enter|leave)", text, re.IGNORECASE))


def _maybe_remember_important_action(content, context):
    """Persist explicit continuity decisions without storing every chat line."""
    text = str(content or "").strip()
    if not context.room_dir or len(text) < 8:
        return
    patterns = (r"(?:进入|前往|来到|离开|跑到|去往|转场|切换场景)", r"(?:带上|带着|留下|加入|护送|跟随)")
    if not any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
        return
    try:
        remember_room_fact({"kind": "player_decision", "content": text, "importance": 3}, context)
        append_room_event(context.room_dir, {"kind": "player_decision", "content": text})
    except Exception:
        logger.exception("Failed to remember important player action")


def _compact_history_entries(summary):
    # Keep the persisted summary useful without imposing an output-token cap on
    # normal KP replies.
    clean = str(summary or "").strip()
    if len(clean) > 4000:
        clean = clean[:3999].rstrip() + "…"
    return [{"role": "system", "content": f"历史压缩摘要：\n{clean}", "compact": True}]


def _compact_history_with_ai(requester, model, history):
    if not history:
        return []

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "请压缩当前桌上角色扮演房间的历史记录。保留当前场景、关键事实、NPC状态、"
                    "每位玩家的行动、未解决线索和检定结果；使用短句和键值格式，不要编造内容。"
                ),
            },
            {"role": "user", "content": _json_for_log(history)},
        ],
    }
    summary, _token_count = _extract_ai_response(requester(payload))
    if not summary.strip():
        raise RuntimeError("AI 平台未返回历史压缩摘要")
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


def _compact_room_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return {}

    scenario = snapshot.get("scenario")
    if isinstance(scenario, dict):
        available_sections = scenario.get("available_sections")
        if not isinstance(available_sections, dict):
            available_sections = {}
        compact_scenario = {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description"),
            "found": scenario.get("found"),
            "available_sections": available_sections,
            "allow_open_ending": scenario.get("allow_open_ending"),
            "module_count": scenario.get("module_count"),
            "trigger_count": scenario.get("trigger_count"),
            "active_scene_id": scenario.get("active_scene_id"),
            "scene_manifest": (scenario.get("scene_manifest", []) if isinstance(scenario.get("scene_manifest", []), list) else [])[:40],
            "global_manifest": (scenario.get("global_manifest", []) if isinstance(scenario.get("global_manifest", []), list) else [])[:12],
            "opening": scenario.get("opening"),
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

    memory = snapshot.get("memory")
    if isinstance(memory, dict) and isinstance(memory.get("items"), list):
        memory = {"items": [
            {**item, "content": str(item.get("content") or "")[:240]}
            for item in memory["items"][:8] if isinstance(item, dict)
        ]}
    return {
        "room": snapshot.get("room"),
        "scenario": compact_scenario,
        "members": members,
        "memory": memory,
        "triggers": snapshot.get("triggers", []),
    }


def _room_snapshot_system_message(snapshot, room_state=None):
    compact_snapshot = _compact_room_snapshot(snapshot)
    if room_state is not None:
        compact_snapshot["state"] = project_room_state(room_state, snapshot)
    return (
        "当前房间资料必须通过工具 `room.get_room_snapshot` 获取。\n"
        "优先使用当前房间、绑定剧本、触发器目录和成员角色卡。\n"
        "不要复用其他房间的剧本、角色或记忆资料。\n"
        "注入的上下文是精简版，不包含完整场景文本或完整角色详情。\n"
        "需要详细剧本模块或触发器内容时，调用相应的房间或触发器工具。\n"
        "需要剧本摘要时先调用 `room.get_scenario_context`，需要完整模块内容时调用 `room.get_scenario_module`。\n"
        "scene_manifest 是剧本提供的唯一场景索引；global_manifest 是背景/公开信息/时间线的短摘要。"
        "若 scenario.sequential=true，优先按照 scene_manifest 的 order 顺序加载模块；否则按玩家当前需求检索。"
        "summary 仅用于检索，不能替代原文，也不能据此推断未写出的设施。\n"
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
            item_content = _wrap_user_input(item_content)
        messages.append({"role": item["role"], "content": item_content})
    messages.append({"role": "user", "content": _wrap_user_input(content)})
    return messages


def _history_for_request(history, max_chars=8000, recent_items=12):
    """Keep prompt history bounded without an extra summarization request.

    Persisted history remains untouched; only the copy sent to the model is
    compacted. Existing explicit ``compact`` summaries are always retained.
    """
    if not isinstance(history, list):
        return []
    pinned = [item for item in history if isinstance(item, dict) and item.get("compact")]
    recent = [item for item in history if isinstance(item, dict) and not item.get("compact")][-recent_items:]
    selected = pinned[-1:] + recent
    total = 0
    result = []
    for item in reversed(selected):
        size = len(str(item.get("content") or ""))
        if result and total + size > max_chars:
            break
        result.append(item)
        total += size
    return list(reversed(result))


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
        requested_role_id = str(message_data.get("role_id") or "").strip()
        if requested_role_id:
            roles = load_roles(_get_role_config_file(), _get_kp_prompt_file(), _get_ai_platform_dir())
            role_config = next((role for role in roles if str(role.get("id")) == requested_role_id), None) or _load_role_for_content(content)
        else:
            role_config = _load_role_for_content(content)
        agent_profile = resolve_agent_profile(
            role_config,
            _get_kp_prompt_file(),
            prefer_prompt_file=str(role_config.get("id") or "kp") == "kp",
        )
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
            request_content=content,
        )
        agent_context.tool_state.update(
            {
                "allow_checks": _request_allows_check(content),
                "allow_unconditional_trigger": _request_allows_manual_trigger(content),
                "allow_scene_transition": _request_allows_scene_transition(content),
            }
        )
        room_snapshot_message = None
        room_snapshot = None
        if room_id:
            room_snapshot = get_room_snapshot({}, agent_context)
            room_snapshot_message = _room_snapshot_system_message(
                room_snapshot,
                agent_context.room_state(),
            )

        runtime_config = load_ai_runtime_config(_get_config_dir())
        model = _select_model(platform_config)
        small_model = str(provider_small_model_config(platform_config, "summarization").get("id") or model)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        requester = _post_ai_request(base_url, headers)
        history_file, history = _load_history(
            user_id,
            room_id=room_id,
            agent_id=agent_profile.id,
        )

        if _is_compact_command(content):
            if history:
                history = _compact_history_with_ai(requester, small_model, history)
                write_json_atomic(history_file, history)
                response_text = "历史记录已压缩。"
            else:
                response_text = "暂无可压缩的历史记录。"
            return success_response(message=None, content=response_text, token_count=None)

        if _history_needs_compaction(history):
            try:
                history = _compact_history_with_ai(requester, small_model, history)
                write_json_atomic(history_file, history)
            except Exception:
                logger.exception("Failed to compact chat history automatically")

        speaker = _speaker_for_user(agent_context.room_info(), user_id) if room_id else None
        user_content = _format_user_content(content, speaker)
        system_prompt = (
            _load_debug_kp_prompt()
            if runtime_config.debug_mode
            else agent_profile.prompt or _load_kp_prompt()
        )
        if not runtime_config.show_ai_hints:
            system_prompt += "\n设置：禁止在回复结尾主动提供提示、选项、行动列表或下一步建议；仅在玩家明确询问时回答。"
        if room_id:
            system_prompt = (
                f"{system_prompt}\n"
                "房间快照中的 scene_manifest/global_manifest 是唯一索引；摘要不是事实。若 sequential=true，优先按 order 顺序加载模块。"
                "仅在用户明确需要时按 ID 加载模块原文；转场先调用 room.activate_scenario_scene，再读模块。"
                "不得创造剧本未写出的地点、设施、NPC、道具或触发器内容；未提供就明确说明。"
                "剧本、房间快照、角色卡和工具返回值是唯一事实来源；不得把猜测写成既定事实。"
                "不要因问候、摘要或关键词自动检定/揭示/记忆；工具完成后立即简短叙事回复。"
            )

        prompt_history = _history_for_request(history)
        scene_static = None
        if isinstance(room_snapshot, dict):
            scenario_data = room_snapshot.get("scenario")
            if isinstance(scenario_data, dict):
                active_scene = scenario_data.get("active_scene_id")
                manifest = scenario_data.get("scene_manifest") if isinstance(scenario_data.get("scene_manifest"), list) else []
                scene_static = next((item for item in manifest if isinstance(item, dict) and str(item.get("id")) == str(active_scene)), None)
        prompt_layers = build_prompt_layers(
            global_rules=system_prompt,
            scenario=(room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else None,
            scene=scene_static,
            room_state=agent_context.room_state() if room_id else {},
            history=prompt_history,
            user_input=user_content,
            rules_version="1",
        )
        if room_snapshot_message:
            prompt_layers.messages.insert(3, {"role": "system", "content": room_snapshot_message})
        request_data = {
            "messages": prompt_layers.messages,
            "model": model,
            "temperature": 0.5,
            "top_p": 0.85,
        }
        if room_id:
            request_data["metadata"] = {
                **request_data.get("metadata", {}),
                "session_id": _room_session_id(room_id, agent_profile.id),
                "room_id": str(room_id),
                "agent_id": agent_profile.id,
                "cache_key": prompt_layers.cache_key,
            }
        if runtime_config.stream_output:
            request_data["stream"] = False

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "Started AI chat"),
            user_id=session.get("user_id") or user_id,
            role=role_config.get("id"),
            platform=selected_platform,
            model=request_data["model"],
            content_length=len(content),
        )
        started_at = time.perf_counter()
        result = run_agent_completion(
            requester=requester,
            base_payload=request_data,
            profile=agent_profile,
            registry=default_tool_registry(),
            context=agent_context,
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        if result.error:
            return error_response("AI agent request failed", 500, result.error)

        prompt_tokens = result.prompt_token_count or 0
        completion_tokens = result.completion_token_count or 0
        total_tokens = result.token_count or (prompt_tokens + completion_tokens)
        cached_tokens = result.cached_token_count or 0
        cache_hit_rate = calculate_cache_hit_rate(prompt_tokens, cached_tokens)
        scenario_info = (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {}
        if not isinstance(scenario_info, dict):
            scenario_info = {}
        cache_key = build_provider_cache_key(
            scenario_info.get("id") or "unknown",
            scenario_info.get("version") or "1",
            scenario_info.get("active_scene_id") or "unknown",
            scenario_info.get("scene_version") or "1",
            "1",
        )
        usage_record = record_ai_usage(
            current_app.config.get("LOGS_DIR", LOGS_DIR),
            {
                "agent_id": agent_profile.id,
                "provider": selected_platform,
                "model": request_data["model"],
                "room_id": str(room_id) if room_id else None,
                "scene_id": scenario_info.get("active_scene_id") if isinstance(scenario_info, dict) else None,
                "cache_key": cache_key,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "elapsed_ms": elapsed_ms,
            },
        )

        direct_message = None
        if isinstance(result.response_data, dict):
            direct_message = result.response_data.get("direct_message")
        direct_messages = result.direct_messages or []
        if direct_message and not direct_messages:
            direct_messages = [direct_message]

        structured = parse_kp_response(result.content)
        validated_updates = {}
        if structured:
            ai_response = structured.narration
            if room_id and structured.state_updates:
                scenario_data = (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {}
                validated_updates = validate_state_updates(
                    structured.state_updates,
                    agent_context.room_state(),
                    scenario_data,
                )
                if validated_updates:
                    apply_state_updates(agent_context.room_dir, validated_updates)
                    append_room_event(
                        agent_context.room_dir,
                        {"kind": "state_update", "content": "AI validated state update", "metadata": validated_updates},
                    )
            if structured.next_scene and room_id and "active_scene_id" not in validated_updates:
                scenario_data = (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {}
                next_updates = validate_state_updates(
                    {"active_scene_id": structured.next_scene},
                    agent_context.room_state(),
                    scenario_data,
                )
                if next_updates:
                    apply_state_updates(agent_context.room_dir, next_updates)
                    validated_updates.update(next_updates)
        else:
            ai_response, _ = _strip_compact_command(result.content)
        _, compact_requested_by_ai = _strip_compact_command(result.content)
        token_count = result.token_count
        if not ai_response and compact_requested_by_ai:
            ai_response = "历史记录已压缩。"
        # A few providers terminate after a successful tool call without a
        # second assistant message. Keep the tool/direct message visible and
        # return a normal chat response instead of surfacing a false failure.
        if not ai_response and (result.direct_messages or result.tool_messages):
            ai_response = "已完成检定/场景处理，详情见上方记录。"
        if not ai_response:
            return error_response(
                "AI platform did not return a response",
                400,
                "No response",
            )
        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "Received AI chat response"),
            user_id=session.get("user_id") or user_id,
            platform=selected_platform,
            model=request_data["model"],
            response_length=len(ai_response),
            token_count=token_count,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached_tokens,
            cache_hit_rate=cache_hit_rate,
            elapsed_ms=elapsed_ms,
        )

        user_history_item = {"role": "user", "content": content}
        if speaker:
            user_history_item["speaker"] = speaker
        history.extend([user_history_item, {"role": "assistant", "content": ai_response}])
        _maybe_remember_important_action(content, agent_context)
        if compact_requested_by_ai:
            try:
                history = _compact_history_with_ai(requester, small_model, history)
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
            direct_message=direct_messages[0] if direct_messages else None,
            direct_messages=direct_messages,
            tool_messages=result.tool_messages or [],
            prompt_tokens=usage_record["prompt_tokens"],
            completion_tokens=usage_record["completion_tokens"],
            cached_tokens=usage_record["cached_tokens"],
            cache_hit_rate=usage_record["cache_hit_rate"],
            elapsed_ms=usage_record["elapsed_ms"],
            cache_key=cache_key,
            structured_output=(
                {
                    "options": structured.options,
                    "state_updates": validated_updates,
                    "next_scene": structured.next_scene,
                    "npc_actions": structured.npc_actions,
                }
                if structured
                else None
            ),
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
            user_action_text(session.get("username") or user_id, "Sent a home message"),
            user_id=session.get("user_id") or user_id,
            content_length=len(message_content),
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
            user_action_text(session.get("username") or user_id, "Sent a scenario message"),
            user_id=session.get("user_id") or user_id,
            scenario_id=script_id,
            content_length=len(message_content),
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
