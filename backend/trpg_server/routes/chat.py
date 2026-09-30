import json
import logging
import re
import time
from pathlib import Path
from uuid import uuid4

import requests
from flask import Blueprint, current_app, request, session

from trpg_server.ai_platform_config import load_platform_config
from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.context import build_agent_context
from trpg_server.agents.profiles import AgentProfile, resolve_agent_profile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.structured_output import apply_state_updates, parse_kp_response, validate_state_updates, validate_structured_response
from trpg_server.agents.telemetry import build_provider_cache_key, calculate_cache_hit_rate, record_ai_usage
from trpg_server.agents.prompt_builder import build_prompt_layers
from trpg_server.agents.cache import ExactResponseCache, ProviderPrefixCache, SemanticCache, build_exact_response_key
from trpg_server.agents.knowledge_base import KnowledgeBaseService
from trpg_server.agents.ruleset_knowledge import RulesetKnowledgeStore, search_ruleset
from trpg_server.agents.tools import default_tool_registry
from trpg_server.agents.tools.room import get_room_snapshot
from trpg_server.agents.memory import remember_room_fact
from trpg_server.agents.room_state import append_room_event, project_room_state
from trpg_server.agents.trigger_system import find_trigger_definition, record_trigger, validate_trigger
from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_access_denied, log_user_action, redact_sensitive, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.role_config import load_roles, provider_small_model_config, select_role_for_content
from trpg_server.settings import (
    AI_PLATFORM_SECRET_DIR,
    CONFIG_DIR,
    HISTORY_DIR,
    ROOMS_DIR,
    SCENARIOS_DIR,
    LOGS_DIR,
    KNOWLEDGE_BASES_DIR,
)

bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)
_PREFIX_CACHE = ProviderPrefixCache(default_ttl=3600)
_EXACT_CACHE = ExactResponseCache(default_ttl=300)
_SEMANTIC_CACHE = SemanticCache(default_ttl=120)
_HISTORY_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")
HISTORY_COMPACT_CHAR_THRESHOLD = 12000


def _profile_for_request(profile, tool_state, enable_suggestions=True):
    """Keep the complete KP capability set while removing schema aliases.

    Alias tools execute the same handler and only exist for compatibility with
    older callers. Advertising both names to the model increases ambiguity and
    schema tokens without adding a capability. Request-time safety remains in
    each tool handler; no legitimate tool chain is disabled here.

    ``room.suggest_actions`` is dropped unless the room house rules enable
    action suggestions, so a disabled feature costs no schema tokens.
    """
    names = list(profile.tool_names or [])
    aliases = {"dice.roll_dice", "sanity.roll_sanity_check"}
    gated = set() if enable_suggestions else {"room.suggest_actions"}
    filtered = [name for name in names if name not in aliases and name not in gated]
    return AgentProfile(
        id=profile.id,
        name=profile.name,
        prompt=profile.prompt,
        provider=profile.provider,
        wake_words=profile.wake_words,
        tool_names=filtered,
        context_providers=profile.context_providers,
    )


def _timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _deliver_structured_triggers(room_dir, room_info, scenario, requests):
    """Validate model-selected trigger ids and persist only approved messages."""
    if not room_dir or not isinstance(scenario, dict):
        return []
    messages_path = Path(room_dir) / "messages.json"
    messages = read_json(messages_path, default=[])
    if not isinstance(messages, list):
        messages = []
    state = read_json(Path(room_dir) / "state.json", default={})
    state = state if isinstance(state, dict) else {}
    delivered = []
    from trpg_server.scenario_store import build_trigger_message
    for requested in requests if isinstance(requests, list) else []:
        trigger_id = str(requested.get("trigger_id") or "").strip() if isinstance(requested, dict) else ""
        if not trigger_id:
            continue
        definition = find_trigger_definition(scenario, trigger_id)
        if definition:
            validation = validate_trigger(trigger_id, {**state, "scenario_version": room_info.get("scenario_version")}, scenario, audience="player")
            if not validation.get("ok"):
                logger.info("structured_trigger_rejected room_id=%s trigger_id=%s reason=%s", room_info.get("id"), trigger_id, validation.get("reason"))
                continue
            body = []
            for attachment in definition.get("attachments", []):
                resource = attachment.get("resourceRef") or {}
                if resource.get("content"):
                    body.append(str(resource["content"]))
                elif resource.get("url"):
                    body.append(f"[{resource.get('alt')}]({resource.get('url')})")
            message = {"type": "trigger", "sender_id": None, "sender_name": definition.get("text") or f"触发器{trigger_id}", "avatar": "/assets/avatars/default_system.jpg", "content": "\n\n".join(body), "time": time.strftime("%H:%M"), "created_at": _timestamp(), "metadata": {"trigger_id": trigger_id, "reason": requested.get("reason", "")}}
        else:
            message = build_trigger_message(scenario, trigger_id)
            if not message:
                continue
            message = {**message, "id": uuid4().hex, "sender_id": None, "time": time.strftime("%H:%M"), "created_at": _timestamp(), "metadata": {**(message.get("metadata") or {}), "reason": requested.get("reason", "")}}
        messages.append(message)
        delivered.append(message)
        record_trigger(room_dir, trigger_id, reason=str(requested.get("reason") or "AI trigger"))
        state = read_json(Path(room_dir) / "state.json", default=state)
    if delivered:
        write_json_atomic(messages_path, messages[-200:])
    return delivered


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


def _can_start_scenario(room_info, user_id, global_role="USER"):
    if str(global_role or "").upper() in {"ADMIN", "OWNER"}:
        return True
    if str(room_info.get("creator_id")) == str(user_id):
        return True
    for member in room_info.get("members", []):
        if str(member.get("user_id")) != str(user_id):
            continue
        if member.get("is_active", True) is False or member.get("status", "active") == "removed":
            return False
        return member.get("room_role") in {"owner", "admin"}
    return False


def _build_knowledge_usage(result, scenario_results):
    ruleset = getattr(result, "knowledge_usage", None)
    ruleset = ruleset if isinstance(ruleset, dict) else {}
    scenario_chunks = len(scenario_results) if isinstance(scenario_results, list) else 0
    ruleset_chunks = int(ruleset.get("ruleset_chunks") or 0)
    ruleset_calls = int(ruleset.get("tool_calls") or 0)
    return {
        "used": bool(ruleset_chunks or scenario_chunks),
        "total_chunks": ruleset_chunks + scenario_chunks,
        "ruleset": {
            "called": ruleset_calls > 0,
            "calls": ruleset_calls,
            "chunks": ruleset_chunks,
            "sources": int(ruleset.get("ruleset_sources") or 0),
            "ruleset_ids": list(ruleset.get("ruleset_ids") or []),
            "knowledge_versions": list(ruleset.get("knowledge_versions") or []),
            "topics": list(ruleset.get("topics") or []),
            "citations": list(ruleset.get("citations") or []),
        },
        "scenario": {"chunks": scenario_chunks},
    }


def _mark_scenario_started(room_dir, user_id):
    info_path = room_dir / "info.json"
    room_info = read_json(info_path, default={})
    started_at = room_info.get("scenario_started_at") or _timestamp()
    room_info["scenario_started_at"] = started_at
    room_info["scenario_started_by"] = user_id
    write_json_atomic(info_path, room_info)
    return started_at


def _sync_room_active_scene(room_dir, scene_id, scenario):
    """Mirror a state-update scene transition into ``info.json``.

    Structured KP responses persist ``active_scene_id`` into ``state.json``,
    while the room snapshot, scenario tools and archive checks read the pointer
    from ``info.json`` (which ``room.activate_scenario_scene`` writes). Keeping
    both in sync avoids the model receiving two different "current scenes".
    """
    if not room_dir or scene_id in (None, ""):
        return
    info_path = Path(room_dir) / "info.json"
    info = read_json(info_path, default={})
    if not isinstance(info, dict) or str(info.get("active_scene_id") or "") == str(scene_id):
        return
    info["active_scene_id"] = str(scene_id)
    manifest = scenario.get("scene_manifest") if isinstance(scenario, dict) and isinstance(scenario.get("scene_manifest"), list) else []
    module = next(
        (item for item in manifest if isinstance(item, dict) and str(item.get("id") or item.get("module_id")) == str(scene_id)),
        None,
    )
    if module:
        info["active_scene_title"] = module.get("title")
    write_json_atomic(info_path, info)


def _json_for_log(value):
    return json.dumps(redact_sensitive(value), ensure_ascii=False, default=str)


def _emit_thinking_stage(room_id, ai_request_id, stage, label):
    """Best-effort stage updates for connected clients; never block chat."""
    if not room_id or not ai_request_id:
        return
    try:
        socketio = current_app.extensions.get("socketio")
        if socketio is None:
            return
        socketio.emit(
            "new_message",
            {
                "room_id": str(room_id),
                "type": "ai_thinking_stage",
                "aiRequestId": str(ai_request_id),
                "stage": stage,
                "label": label,
            },
            room=str(room_id),
            namespace="/",
        )
    except Exception:
        logger.debug("Unable to emit AI thinking stage", exc_info=True)


def _post_ai_request(base_url, headers):
    def response_detail(response):
        try:
            detail = response.json()
            return detail.get("error", detail) if isinstance(detail, dict) else detail
        except (ValueError, requests.exceptions.JSONDecodeError):
            return str(getattr(response, "text", ""))[:500]

    def provider_requires_json(status_code, detail):
        text = str(detail).lower()
        return (
            status_code == 400
            and "response_format" in text
            and "json_object" in text
            and "must contain" in text
            and "json" in text
        )

    def requester(payload):
        logger.info("AI API request payload: %s", _json_for_log(payload))
        response = requests.post(base_url, headers=headers, json=payload, timeout=300)
        if not response.ok:
            detail = response_detail(response)
            if provider_requires_json(response.status_code, detail):
                retry_payload = {**payload}
                retry_messages = [dict(message) for message in payload.get("messages", [])]
                if not any("json" in str(message.get("content", "")).lower() for message in retry_messages):
                    retry_messages.append(
                        {
                            "role": "system",
                            "content": "Return the final answer as valid JSON. The response must be a JSON object.",
                        }
                    )
                retry_payload["messages"] = retry_messages
                logger.warning("AI API retry after provider JSON response_format validation failure")
                logger.info("AI API retry request payload: %s", _json_for_log(retry_payload))
                response = requests.post(base_url, headers=headers, json=retry_payload, timeout=300)
                if not response.ok:
                    detail = response_detail(response)
            if not response.ok:
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


def _bounded_manifest_entries(items, max_count, char_cap, text_keys=("summary", "description", "content")):
    """Bound total entry count and per-entry text length of a manifest list."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if len(result) >= max_count:
            break
        if not isinstance(item, dict):
            result.append(item)
            continue
        bounded = dict(item)
        if char_cap:
            for key in text_keys:
                value = bounded.get(key)
                if isinstance(value, str) and value:
                    bounded[key] = value[:char_cap]
        result.append(bounded)
    return result


def _compact_room_snapshot(snapshot, runtime_config=None):
    if not isinstance(snapshot, dict):
        return {}
    scene_manifest_cap = getattr(runtime_config, "max_snapshot_scene_manifest", None)
    if scene_manifest_cap is None:
        scene_manifest_cap = 30
    char_cap = getattr(runtime_config, "snapshot_manifest_summary_cap", None)
    include_entity = getattr(runtime_config, "snapshot_include_entity_manifest", False)

    scenario = snapshot.get("scenario")
    if isinstance(scenario, dict):
        available_sections = scenario.get("available_sections")
        if not isinstance(available_sections, dict):
            available_sections = {}
        entity_manifest = (scenario.get("entity_manifest", []) if isinstance(scenario.get("entity_manifest", []), list) else [])
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
            "scene_manifest": _bounded_manifest_entries(
                (scenario.get("scene_manifest", []) if isinstance(scenario.get("scene_manifest", []), list) else []),
                scene_manifest_cap,
                char_cap,
            ),
            "global_manifest": _bounded_manifest_entries(
                (scenario.get("global_manifest", []) if isinstance(scenario.get("global_manifest", []), list) else []),
                12,
                char_cap,
            ),
        }
        if include_entity and entity_manifest:
            compact_scenario["entity_manifest"] = _bounded_manifest_entries(entity_manifest, scene_manifest_cap, char_cap)
        opening = scenario.get("opening")
        if isinstance(opening, str) and opening and char_cap:
            opening = opening[:char_cap]
        compact_scenario["opening"] = opening
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
    triggers = snapshot.get("triggers", [])
    if isinstance(triggers, list):
        triggers = _bounded_manifest_entries(triggers, scene_manifest_cap, char_cap)
    else:
        triggers = snapshot.get("triggers", [])
    return {
        "room": snapshot.get("room"),
        "scenario": compact_scenario,
        "members": members,
        "memory": memory,
        "triggers": triggers,
    }


def _room_snapshot_system_message(snapshot, room_state=None, runtime_config=None):
    compact_snapshot = _compact_room_snapshot(snapshot, runtime_config)
    if room_state is not None:
        compact_snapshot["state"] = project_room_state(room_state, snapshot)
    return (
        "当前房间资料必须通过工具 `room.get_room_snapshot` 获取。\n"
        "优先使用当前房间、绑定剧本、触发器目录和成员角色卡。\n"
        "不要复用其他房间的剧本、角色或记忆资料。\n"
        "注入的上下文是精简版，不包含完整场景文本或完整角色详情。\n"
        "需要详细剧本模块或触发器内容时，调用相应的房间或触发器工具。\n"
        "需要剧本摘要时先调用 `room.get_scenario_context`；只有检索片段不足以回答时，才调用 `room.get_scenario_module` 读取有界原文片段。\n"
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
        if room_id:
            _room_archived_check = read_json(
                Path(current_app.config.get("ROOMS_DIR", ROOMS_DIR)) / str(room_id) / "info.json",
                default={},
            )
            if isinstance(_room_archived_check, dict) and _room_archived_check.get("archived"):
                log_access_denied(
                    logger,
                    user_action_text(session.get("username"), "访问房间被拒绝"),
                    用户ID=session.get("user_id"),
                    房间ID=room_id,
                    原因="房间已归档",
                )
                return error_response("Room is archived", 403, "归档房间已关闭 AI，无法继续调用；仍可使用骰娘与其他房间工具")
        scenario_start = message_data.get("scenario_start") is True
        if scenario_start and agent_profile.id != "kp":
            return error_response("Scenario start must use the KP agent", 400, "KP agent required")
        ai_request_id = str(message_data.get("ai_request_id") or "").strip()
        agent_context = build_agent_context(
            room_id=room_id,
            rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
            scenarios_dir=current_app.config.get("SCENARIOS_DIR", SCENARIOS_DIR),
            user_id=user_id,
            agent_id=agent_profile.id,
            request_content=content,
        )
        if scenario_start:
            if not room_id or not agent_context.room_dir:
                return error_response("A room is required to start the scenario", 400, "Room is required")
            room_info = agent_context.room_info()
            session_user_id = session.get("user_id")
            if session_user_id is None or not _can_start_scenario(room_info, session_user_id, session.get("role")):
                return error_response("Permission denied", 403, "Only room managers can start the scenario")
            if room_info.get("scenario_started_at"):
                return error_response("Scenario has already started", 409, "Scenario already started")
            content = (
                "@KP [系统开场任务] 请读取当前房间快照和起始场景所需的剧本模块，"
                "直接为所有玩家进行简洁、有代入感的开场导入。不要声称玩家说了‘开始’，"
                "不要替玩家决定行动，不要在结尾列出选项。"
            )
            agent_context = build_agent_context(
                room_id=room_id,
                rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
                scenarios_dir=current_app.config.get("SCENARIOS_DIR", SCENARIOS_DIR),
                user_id=session_user_id,
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
        ruleset_metrics = {"latency_ms": 0.0}
        if room_id:
            ruleset_store = RulesetKnowledgeStore(
                current_app.config.get("KNOWLEDGE_BASES_DIR", KNOWLEDGE_BASES_DIR),
                rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
            )

            def ruleset_search(query, top_k):
                started = time.perf_counter()
                _emit_thinking_stage(room_id, ai_request_id, "ruleset_search", "正在查询规则书")
                try:
                    return search_ruleset(room_id, query, store=ruleset_store, top_k=top_k)
                finally:
                    ruleset_metrics["latency_ms"] += round((time.perf_counter() - started) * 1000, 2)

            agent_context.tool_state["ruleset_search"] = ruleset_search
        if room_id and ai_request_id:
            agent_context.tool_state["thinking_stage_callback"] = lambda stage, label: _emit_thinking_stage(
                room_id, ai_request_id, stage, label
            )
        runtime_config = load_ai_runtime_config(_get_config_dir())
        room_snapshot_message = None
        room_snapshot = None
        # Action suggestions are gated by the global hint switch (authoritative)
        # AND the per-room house rule, which defaults to off.
        house_rules = agent_context.room_info().get("house_rules") if room_id else {}
        house_rules = house_rules if isinstance(house_rules, dict) else {}
        effective_suggestions = bool(runtime_config.show_ai_hints) and bool(
            house_rules.get("action_suggestions_enabled")
        )
        if room_id:
            agent_context.tool_state["allow_action_suggestions"] = effective_suggestions
        request_profile = _profile_for_request(
            agent_profile,
            agent_context.tool_state,
            enable_suggestions=effective_suggestions,
        )
        if room_id:
            room_snapshot = get_room_snapshot({}, agent_context)
            room_snapshot_message = _room_snapshot_system_message(room_snapshot, None, runtime_config)
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

        speaker = None if scenario_start else (_speaker_for_user(agent_context.room_info(), user_id) if room_id else None)
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
                "最终回复必须是有效的 JSON 对象（JSON object），不要输出 JSON 之外的内容。"
                "房间快照中的 scene_manifest/global_manifest 是唯一索引；摘要不是事实。若 sequential=true，优先按 order 顺序加载模块。"
                "仅在用户明确需要时按 ID 加载模块原文；转场先调用 room.activate_scenario_scene，再读模块。"
                "不得创造剧本未写出的地点、设施、NPC、道具或触发器内容；未提供就明确说明。"
                "剧本、房间快照、角色卡和工具返回值是唯一事实来源；不得把猜测写成既定事实。"
                "不要因问候、摘要或关键词自动检定/揭示/记忆；工具完成后立即简短叙事回复。"
                "本轮已注入房间快照、动态状态和剧本知识库检索结果，不要重复调用 room.get_room_snapshot；"
                "检索结果足够回答时不要再调用 room.get_scenario_context 或 room.get_scenario_module。"
                "明确检定时直接调用对应检定工具；得到结果后直接生成最终叙事，除非已知触发条件要求继续调用触发器。"
                "禁止使用相同参数重复调用同一工具；互不依赖的工具应在同一轮并行调用。"
                "只有明确到达结局或满足剧本结束条件时，才在 state_updates 中设置 completed 或 ending_reached 为 true。"
            )

        prompt_history = _history_for_request(history)
        scene_static = None
        if isinstance(room_snapshot, dict):
            scenario_data = room_snapshot.get("scenario")
            if isinstance(scenario_data, dict):
                active_scene = scenario_data.get("active_scene_id")
                manifest = scenario_data.get("scene_manifest") if isinstance(scenario_data.get("scene_manifest"), list) else []
                scene_static = next((item for item in manifest if isinstance(item, dict) and str(item.get("id")) == str(active_scene)), None)
        scenario_results = []
        if room_id:
            _emit_thinking_stage(room_id, ai_request_id, "vector_search", "正在调用向量库")
            try:
                scenario_results = KnowledgeBaseService(
                    rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
                    scenarios_dir=current_app.config.get("SCENARIOS_DIR", SCENARIOS_DIR),
                    vector_store=current_app.extensions.get("vector_store"),
                    embedding_provider=current_app.extensions.get("embedding_provider"),
                ).search(room_id, content, top_k=3)
                scenario_results = [
                    item for item in scenario_results
                    if isinstance(item, dict) and str(item.get("text") or "").strip()
                ]
            except (OSError, ValueError):
                logger.exception("Scenario retrieval failed")
        rules_version = str((agent_context.room_info().get("rulesets") or {}).get("coc7") or "1") if room_id else "1"
        projected_state = project_room_state(agent_context.room_state(), room_snapshot) if room_id else {}
        if effective_suggestions and isinstance(projected_state, dict):
            # Only AI-relevant active house rules reach the prompt, injected into
            # the dynamic room-state layer so the static prefix stays cacheable.
            projected_state["house_rules"] = {
                "ai_next_step_hints": "用 room.suggest_actions 返回；不要在正文列出选项"
            }
        prompt_layers = build_prompt_layers(
            global_rules=system_prompt,
            scenario=(room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else None,
            scene=scene_static,
            room_state=projected_state,
            history=prompt_history,
            user_input=user_content,
            rules_version=rules_version,
            retrieval_results=scenario_results,
            ruleset_results=[],
        )
        _emit_thinking_stage(room_id, ai_request_id, "vector_search_done", "向量库检索完成")
        if room_snapshot_message:
            prompt_layers.messages.insert(3, {"role": "system", "content": room_snapshot_message})
        prefix_cache_hit = _PREFIX_CACHE.lookup(prompt_layers.cache_key)
        scenario_info_for_cache = (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {}
        scenario_info_for_cache = scenario_info_for_cache if isinstance(scenario_info_for_cache, dict) else {}
        state_for_cache = agent_context.room_state() if room_id else {}
        exact_cache_key = build_exact_response_key(
            scenario_info_for_cache.get("id") or "unknown",
            scenario_info_for_cache.get("scenario_version") or scenario_info_for_cache.get("version") or "1",
            scenario_info_for_cache.get("active_scene_id") or "unknown",
            state_for_cache,
            content,
        )
        semantic_state = {
            "room_id": str(room_id or "home"),
            "scenario_id": scenario_info_for_cache.get("id"),
            "scenario_version": scenario_info_for_cache.get("scenario_version") or scenario_info_for_cache.get("version") or "1",
            "active_scene_id": scenario_info_for_cache.get("active_scene_id"),
            "state": state_for_cache,
        }
        cached_result = None if scenario_start else (_EXACT_CACHE.get(exact_cache_key) if not room_id else _SEMANTIC_CACHE.get(content, semantic_state))
        if isinstance(cached_result, dict) and cached_result.get("content"):
            _emit_thinking_stage(room_id, ai_request_id, "finalizing", "正在整理回复")
            cached_knowledge_usage = cached_result.get("knowledge_usage") or {
                "used": bool(scenario_results),
                "total_chunks": len(scenario_results),
                "ruleset": {"called": False, "calls": 0, "chunks": 0, "sources": 0, "ruleset_ids": [], "knowledge_versions": [], "topics": [], "citations": []},
                "scenario": {"chunks": len(scenario_results)},
            }
            cached_knowledge_usage = {**cached_knowledge_usage, "cached": True}
            record_ai_usage(
                current_app.config.get("LOGS_DIR", LOGS_DIR),
                {
                    "agent_id": agent_profile.id,
                    "provider": selected_platform,
                    "model": model,
                    "room_id": str(room_id) if room_id else None,
                    "scenario_id": scenario_info_for_cache.get("id") or None,
                    "scenario_version": scenario_info_for_cache.get("scenario_version") or scenario_info_for_cache.get("version") or "1",
                    "scene_id": scenario_info_for_cache.get("active_scene_id") or None,
                    "cache_key": prompt_layers.cache_key,
                    "cache_layer": "semantic" if room_id else "exact",
                    "prefix_cache_hit": True,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cached_tokens": 0,
                    "total_tokens": 0,
                    "ruleset_ids": cached_knowledge_usage.get("ruleset", {}).get("ruleset_ids", []),
                    "knowledge_versions": cached_knowledge_usage.get("ruleset", {}).get("knowledge_versions", []),
                    "retrieval_topics": cached_knowledge_usage.get("ruleset", {}).get("topics", []),
                    "retrieval_chunk_count": cached_knowledge_usage.get("ruleset", {}).get("chunks", 0),
                    "retrieval_latency_ms": 0,
                    "retrieval_citations": cached_knowledge_usage.get("ruleset", {}).get("citations", []),
                },
            )
            return success_response(
                message=None,
                content=cached_result["content"],
                token_count=cached_result.get("token_count"),
                prompt_tokens=0,
                completion_tokens=0,
                cached_tokens=0,
                cache_hit_rate=100.0,
                cache_key=prompt_layers.cache_key,
                prefix_cache_hit=True,
                knowledge_usage=cached_knowledge_usage,
                structured_output=cached_result.get("structured_output"),
            )
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
            request_data["response_format"] = {"type": "json_object"}
        if runtime_config.stream_output:
            request_data["stream"] = False

        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "开始 AI 对话"),
            用户ID=session.get("user_id") or user_id,
            角色=role_config.get("id"),
            平台=selected_platform,
            模型=request_data["model"],
            内容长度=len(content),
        )
        started_at = time.perf_counter()
        result = run_agent_completion(
            requester=requester,
            base_payload=request_data,
            profile=request_profile,
            registry=default_tool_registry(),
            context=agent_context,
            max_tool_result_chars=runtime_config.max_tool_result_chars,
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        if result.error:
            _emit_thinking_stage(room_id, ai_request_id, "error", "AI 请求失败")
            return error_response("AI agent request failed", 500, result.error)

        knowledge_usage = _build_knowledge_usage(result, scenario_results)

        _emit_thinking_stage(room_id, ai_request_id, "finalizing", "正在整理回复")

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
                "scenario_id": scenario_info.get("id") if isinstance(scenario_info, dict) else None,
                "scenario_version": (scenario_info.get("scenario_version") or scenario_info.get("version")) if isinstance(scenario_info, dict) else None,
                "cache_key": cache_key,
                "prefix_cache_hit": prefix_cache_hit,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "elapsed_ms": elapsed_ms,
                "ruleset_ids": knowledge_usage["ruleset"]["ruleset_ids"],
                "knowledge_versions": knowledge_usage["ruleset"]["knowledge_versions"],
                "retrieval_topics": knowledge_usage["ruleset"]["topics"],
                "retrieval_chunk_count": knowledge_usage["ruleset"]["chunks"],
                "retrieval_latency_ms": ruleset_metrics["latency_ms"],
                "retrieval_citations": knowledge_usage["ruleset"]["citations"],
                "scenario_retrieval_chunk_count": knowledge_usage["scenario"]["chunks"],
                "agent_request_rounds": int(agent_context.tool_state.get("agent_request_rounds") or 0),
                "agent_tool_calls": list(agent_context.tool_state.get("tool_call_trace") or []),
            },
        )

        direct_message = None
        if isinstance(result.response_data, dict):
            direct_message = result.response_data.get("direct_message")
        direct_messages = result.direct_messages or []
        if direct_message and not direct_messages:
            direct_messages = [direct_message]

        # Action options staged by the KP via room.suggest_actions. These are
        # rendered as buttons in the chat UI (owner-interactive, read-only for
        # other room members) and never persisted as room messages.
        suggestions = []
        staged_suggestions = agent_context.tool_state.get("suggested_actions")
        if isinstance(staged_suggestions, list):
            suggestions = [str(item) for item in staged_suggestions if str(item).strip()]

        structured = parse_kp_response(result.content)
        if structured:
            structured = validate_structured_response(structured, (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {})
        validated_updates = {}
        delivered_structured_triggers = []
        ending_reached = False
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
            if room_id and validated_updates.get("active_scene_id"):
                _sync_room_active_scene(
                    agent_context.room_dir,
                    validated_updates["active_scene_id"],
                    (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else None,
                )
            # Reaching an ending is the only automatic completion signal.  It
            # enables the manager-facing archive action without deleting a
            # still-running room.
            if room_id and agent_context.room_dir:
                ending_id = validated_updates.get("active_scene_id") or structured.next_scene
                scenario_for_completion = (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {}
                manifest = scenario_for_completion.get("scene_manifest", []) if isinstance(scenario_for_completion, dict) else []
                if validated_updates.get("completed") or validated_updates.get("ending_reached") or (ending_id and any(isinstance(item, dict) and str(item.get("id") or item.get("module_id")) == str(ending_id) and str(item.get("type") or "").lower() == "ending" for item in manifest)):
                    ending_reached = True
                    room_info_path = agent_context.room_dir / "info.json"
                    room_info = read_json(room_info_path, default={})
                    if isinstance(room_info, dict) and not room_info.get("completed_at"):
                        room_info["completed_at"] = _timestamp()
                        room_info["completed_by"] = "ai"
                        write_json_atomic(room_info_path, room_info)
            if structured.triggered_files and agent_context.room_dir:
                scenario_data = (room_snapshot or {}).get("scenario") if isinstance(room_snapshot, dict) else {}
                room_info = (room_snapshot or {}).get("room") if isinstance(room_snapshot, dict) and isinstance((room_snapshot or {}).get("room"), dict) else {}
                delivered_structured_triggers = _deliver_structured_triggers(agent_context.room_dir, room_info, scenario_data, structured.triggered_files)
                if delivered_structured_triggers:
                    direct_messages.extend(delivered_structured_triggers)
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
        if not ai_response and suggestions:
            ai_response = "请从下方选择你的行动。"
        if not ai_response:
            return error_response(
                "AI platform did not return a response",
                400,
                "No response",
            )
        log_user_action(
            logger,
            user_action_text(session.get("username") or user_id, "收到 AI 回复"),
            用户ID=session.get("user_id") or user_id,
            平台=selected_platform,
            模型=request_data["model"],
            回复长度=len(ai_response),
            Token数=token_count,
            输入Token=prompt_tokens,
            输出Token=completion_tokens,
            缓存Token=cached_tokens,
            缓存命中率=cache_hit_rate,
            耗时毫秒=elapsed_ms,
        )

        user_history_item = {"role": "system" if scenario_start else "user", "content": content}
        if speaker:
            user_history_item["speaker"] = speaker
        history.extend([user_history_item, {"role": "assistant", "content": ai_response}])
        if not result.tool_messages and not direct_messages and not validated_updates and structured is None and not suggestions:
            cache_value = {"content": ai_response, "token_count": token_count, "structured_output": None, "knowledge_usage": knowledge_usage}
            if room_id:
                _SEMANTIC_CACHE.set(content, semantic_state, cache_value)
            else:
                _EXACT_CACHE.set(exact_cache_key, cache_value)
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

        scenario_started_at = None
        if scenario_start and agent_context.room_dir:
            scenario_started_at = _mark_scenario_started(agent_context.room_dir, session.get("user_id"))
            logger.info("scenario_started room_id=%s user_id=%s", room_id, session.get("user_id"))

        return success_response(
            message=None,
            content=ai_response,
            token_count=token_count,
            direct_message=direct_messages[0] if direct_messages else None,
            direct_messages=direct_messages,
            tool_messages=result.tool_messages or [],
            suggestions=suggestions,
            suggestions_owner=user_id if suggestions else None,
            prompt_tokens=usage_record["prompt_tokens"],
            completion_tokens=usage_record["completion_tokens"],
            cached_tokens=usage_record["cached_tokens"],
            cache_hit_rate=usage_record["cache_hit_rate"],
            elapsed_ms=usage_record["elapsed_ms"],
            cache_key=cache_key,
            prefix_cache_hit=prefix_cache_hit,
            knowledge_usage=knowledge_usage,
            scenario_started_at=scenario_started_at,
            ending_reached=ending_reached,
            structured_output=(
                {
                    "options": structured.options,
                    "state_updates": validated_updates,
                    "next_scene": structured.next_scene,
                    "npc_actions": structured.npc_actions,
                    "triggered_files": structured.triggered_files,
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
            user_action_text(session.get("username") or user_id, "发送了首页消息"),
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
            user_action_text(session.get("username") or user_id, "发送了剧本消息"),
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
