import logging
import time
from uuid import uuid4

from flask import Blueprint, current_app, request, session

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.security import safe_join
from trpg_server.settings import ROOMS_DIR

bp = Blueprint("rooms", __name__)
logger = logging.getLogger(__name__)

USER_ROOM_LIMIT = 3
ELEVATED_ROLES = {"ADMIN", "OWNER"}
ROOM_ROLE_OWNER = "owner"
ROOM_ROLE_ADMIN = "admin"
ROOM_ROLE_MEMBER = "member"
ROOM_MEMBER_ACTIVE = "active"
ROOM_MEMBER_REMOVED = "removed"


def _get_rooms_dir():
    return current_app.config.get("ROOMS_DIR", ROOMS_DIR)


def _timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _require_login():
    if "user_id" not in session:
        return error_response("Please login first", 401, "Not logged in")
    return None


def _is_elevated():
    return session.get("role") in ELEVATED_ROLES


def _iter_room_dirs():
    rooms_dir = _get_rooms_dir()
    if not rooms_dir.exists():
        return []
    return [path for path in rooms_dir.iterdir() if path.is_dir()]


def _read_room(room_dir):
    return read_json(room_dir / "info.json", default={})


def _write_room(room_dir, info):
    info["updated_at"] = _timestamp()
    write_json_atomic(room_dir / "info.json", info)


def _room_dir(room_id):
    return safe_join(_get_rooms_dir(), room_id)


def _find_room(room_id):
    room_dir = _room_dir(room_id)
    info_file = room_dir / "info.json"
    if not info_file.exists():
        return None, None
    return room_dir, read_json(info_file, default={})


def _find_room_by_code(room_code):
    normalized = str(room_code or "").strip().upper()
    for room_dir in _iter_room_dirs():
        info = _read_room(room_dir)
        if info.get("room_code") == normalized:
            return room_dir, info
    return None, None


def _normalize_room_name(room_name):
    return str(room_name or "").strip().casefold()


def _find_room_by_name(room_name):
    normalized = _normalize_room_name(room_name)
    if not normalized:
        return None, None
    for room_dir in _iter_room_dirs():
        info = _read_room(room_dir)
        if _normalize_room_name(info.get("name")) == normalized:
            return room_dir, info
    return None, None


def _room_name_exists(room_name):
    room_dir, _ = _find_room_by_name(room_name)
    return room_dir is not None


def _can_access(info):
    if _is_elevated():
        return True
    user_id = session.get("user_id")
    return _find_member(info, user_id=user_id, active_only=True) is not None


def _can_manage(info):
    return _is_elevated() or info.get("creator_id") == session.get("user_id")


def _current_member(character_card=None):
    user_id = session["user_id"]
    user = None
    try:
        user = current_app.config.get("USER_MANAGER").get_user_by_id(user_id)
    except AttributeError:
        from trpg_server.users.manager import user_manager

        user = user_manager.get_user_by_id(user_id)

    avatar = "/assets/avatars/default.jpg"
    if user:
        avatar = user.get("avatar") or avatar

    member = {
        "user_id": user_id,
        "username": session.get("username", "user"),
        "role": session.get("role", "USER"),
        "room_role": ROOM_ROLE_MEMBER,
        "status": ROOM_MEMBER_ACTIVE,
        "is_active": True,
        "avatar": avatar,
        "joined_at": _timestamp(),
    }
    if character_card:
        member["character_card"] = _sanitize_character_card(character_card)
        member["character_state"] = _initial_character_state(member["character_card"])
    return member


def _sanitize_character_card(character_card):
    if not isinstance(character_card, dict):
        return None

    name = str(character_card.get("name", "")).strip()
    card_id = str(character_card.get("id", "")).strip()
    if not name or not card_id:
        return None

    attributes = character_card.get("attributes") if isinstance(character_card.get("attributes"), dict) else {}
    sanitized = {
        "id": card_id[:80],
        "name": name[:80],
        "occupationId": str(character_card.get("occupationId", character_card.get("occupation_id", "")))[:80],
        "attributes": attributes,
        "maxHp": _bounded_int(character_card.get("maxHp", character_card.get("max_hp")), 1, 999, 1),
        "maxSan": _bounded_int(character_card.get("maxSan", character_card.get("max_san")), 0, 999, 0),
        "mov": _bounded_int(character_card.get("mov"), 0, 99, 0),
        "skills": character_card.get("skills", []) if isinstance(character_card.get("skills", []), list) else [],
        "equipment": character_card.get("equipment", []) if isinstance(character_card.get("equipment", []), list) else [],
        "background": character_card.get("background", {}) if isinstance(character_card.get("background", {}), dict) else {},
    }
    return sanitized


def _bounded_int(value, minimum, maximum, fallback):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, parsed))


def _initial_character_state(character_card):
    max_hp = _bounded_int(character_card.get("maxHp"), 1, 999, 1)
    max_san = _bounded_int(character_card.get("maxSan"), 0, 999, 0)
    return {
        "max_hp": max_hp,
        "current_hp": max_hp,
        "max_san": max_san,
        "current_san": max_san,
        "injury_records": [],
        "sanity_records": [],
    }


def _ensure_character_state(member):
    if not member.get("character_state"):
        member["character_state"] = _initial_character_state(member.get("character_card") or {})
    state = member["character_state"]
    state.setdefault("injury_records", [])
    state.setdefault("sanity_records", [])
    state["max_hp"] = _bounded_int(state.get("max_hp"), 1, 999, 1)
    state["current_hp"] = _bounded_int(state.get("current_hp"), 0, state["max_hp"], state["max_hp"])
    state["max_san"] = _bounded_int(state.get("max_san"), 0, 999, 0)
    state["current_san"] = _bounded_int(state.get("current_san"), 0, state["max_san"], state["max_san"])
    return state


def _bind_character(member, character_card):
    sanitized = _sanitize_character_card(character_card)
    if not sanitized:
        return False
    member["character_card"] = sanitized
    member["character_state"] = _initial_character_state(sanitized)
    return True


def _can_bind_character_card(character_card, target_member):
    if _is_elevated():
        return True
    player_id = str((character_card or {}).get("playerId") or "")
    return player_id in {
        str(target_member.get("user_id")),
        str(target_member.get("username")),
    }


def _is_active_member(member):
    return member.get("is_active", True) is not False and member.get("status", ROOM_MEMBER_ACTIVE) != ROOM_MEMBER_REMOVED


def _find_member(info, user_id=None, username=None, active_only=False):
    for member in info.get("members", []):
        if active_only and not _is_active_member(member):
            continue
        if user_id is not None and str(member.get("user_id")) == str(user_id):
            return member
        if username and str(member.get("username", "")).lower() == str(username).lower():
            return member
    return None


def _normalize_members(info):
    creator_id = str(info.get("creator_id"))
    for member in info.setdefault("members", []):
        member.setdefault("status", ROOM_MEMBER_ACTIVE)
        member.setdefault("is_active", member.get("status") != ROOM_MEMBER_REMOVED)
        if str(member.get("user_id")) == creator_id:
            member["room_role"] = ROOM_ROLE_OWNER
            member["status"] = ROOM_MEMBER_ACTIVE
            member["is_active"] = True
        else:
            member.setdefault("room_role", ROOM_ROLE_MEMBER)
    return info["members"]


def _room_permission(member, info):
    if _is_elevated() or session.get("role") in ELEVATED_ROLES:
        return ROOM_ROLE_ADMIN
    if not member or not _is_active_member(member):
        return ""
    if str(member.get("user_id")) == str(info.get("creator_id")):
        return ROOM_ROLE_OWNER
    return member.get("room_role") or ROOM_ROLE_MEMBER


def _can_manage_members(info):
    member = _find_member(info, user_id=session.get("user_id"), active_only=True)
    return _is_elevated() or _room_permission(member, info) in {ROOM_ROLE_OWNER, ROOM_ROLE_ADMIN}


def _recalculate_character_state(state):
    damage = sum(_bounded_int(record.get("value", record.get("damage")), 0, 999, 0) for record in state.get("injury_records", []))
    san_loss = sum(_bounded_int(record.get("value", record.get("loss")), 0, 999, 0) for record in state.get("sanity_records", []))
    state["current_hp"] = max(0, state["max_hp"] - damage)
    state["current_san"] = max(0, state["max_san"] - san_loss)


def _messages_file(room_dir):
    return room_dir / "messages.json"


def _read_messages(room_dir):
    return read_json(_messages_file(room_dir), default=[])


def _write_messages(room_dir, messages):
    write_json_atomic(_messages_file(room_dir), messages)


def _new_room_code():
    existing = {
        _read_room(room_dir).get("room_code")
        for room_dir in _iter_room_dirs()
    }
    while True:
        code = uuid4().hex[:8].upper()
        if code not in existing:
            return code


def _room_permission_label(member, info):
    if member.get("role") in ELEVATED_ROLES:
        label = "\u7ba1\u7406\u5458"
    elif member.get("room_role") == ROOM_ROLE_OWNER or str(member.get("user_id")) == str(info.get("creator_id")):
        label = "\u623f\u4e3b"
    elif member.get("room_role") == ROOM_ROLE_ADMIN:
        label = "\u7ba1\u7406\u5458"
    else:
        label = "\u6210\u5458"
    if not _is_active_member(member):
        return f"{label}\uff08\u5df2\u79fb\u9664\uff09"
    return label


def _room_summary(info):
    _normalize_members(info)
    return {
        "id": info.get("id"),
        "name": info.get("name"),
        "room_code": info.get("room_code"),
        "scenario_id": info.get("scenario_id"),
        "scenario_title": info.get("scenario_title"),
        "creator_id": info.get("creator_id"),
        "creator_name": info.get("creator_name"),
        "members": [
            {
                **member,
                "is_active": _is_active_member(member),
                "permission_label": _room_permission_label(member, info),
            }
            for member in info.get("members", [])
        ],
        "created_at": info.get("created_at"),
        "updated_at": info.get("updated_at"),
    }


def _created_room_count(user_id):
    return sum(1 for room_dir in _iter_room_dirs() if _read_room(room_dir).get("creator_id") == user_id)


@bp.route("/api/rooms", methods=["GET"])
def list_rooms():
    login_error = _require_login()
    if login_error:
        return login_error

    rooms = []
    for room_dir in _iter_room_dirs():
        info = _read_room(room_dir)
        if _can_access(info):
            rooms.append(_room_summary(info))
    rooms.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return success_response(rooms, "Rooms loaded successfully")


@bp.route("/api/rooms", methods=["POST"])
def create_room():
    login_error = _require_login()
    if login_error:
        return login_error

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    scenario_id = data.get("scenario_id")
    scenario_title = str(data.get("scenario_title", "")).strip()
    if not name:
        return error_response("Please enter room name", 400, "Room name is required")
    if scenario_id is None:
        return error_response("Please choose a scenario", 400, "Scenario is required")
    if _room_name_exists(name):
        return error_response("Room name already exists", 409, "Room name already exists")
    if not _is_elevated() and _created_room_count(session["user_id"]) >= USER_ROOM_LIMIT:
        return error_response(
            "Room creation limit reached",
            403,
            "Room creation limit reached",
        )
    room_id = uuid4().hex
    room_dir = _room_dir(room_id)
    member = _current_member()
    member["room_role"] = ROOM_ROLE_OWNER
    now = _timestamp()
    info = {
        "id": room_id,
        "name": name,
        "room_code": _new_room_code(),
        "scenario_id": scenario_id,
        "scenario_title": scenario_title,
        "creator_id": session["user_id"],
        "creator_name": session.get("username", "user"),
        "members": [member],
        "created_at": now,
        "updated_at": now,
    }
    write_json_atomic(room_dir / "info.json", info)
    _write_messages(room_dir, [])
    write_json_atomic(room_dir / "autosave.json", {"updated_at": now, "messages": []})

    log_user_action(
        logger,
        user_action_text(session.get("username"), "创建了房间"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        房间码=info["room_code"],
        房间名=name,
        剧本=scenario_title,
    )
    return success_response(_room_summary(info), "Room created successfully", 201)


@bp.route("/api/rooms/join", methods=["POST"])
def join_room_by_code():
    login_error = _require_login()
    if login_error:
        return login_error

    data = request.get_json(silent=True) or {}
    room_dir, info = _find_room_by_code(data.get("room_code"))
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")

    user_id = session["user_id"]
    member = _find_member(info, user_id=user_id)
    if not member:
        info.setdefault("members", []).append(_current_member())
        _write_room(room_dir, info)
    elif not _is_active_member(member):
        current_member = _current_member()
        member.update(
            {
                "username": current_member["username"],
                "role": current_member["role"],
                "avatar": current_member["avatar"],
                "status": ROOM_MEMBER_ACTIVE,
                "is_active": True,
                "rejoined_at": _timestamp(),
            }
        )
        _write_room(room_dir, info)

    log_user_action(
        logger,
        user_action_text(session.get("username"), "加入了房间"),
        用户ID=user_id,
        房间ID=info["id"],
        房间码=info.get("room_code"),
        房间名=info.get("name"),
    )
    return success_response(_room_summary(info), "Room joined successfully")


@bp.route("/api/rooms/<room_id>/members/<user_id>/character", methods=["PUT"])
def bind_room_member_character(room_id, user_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    target = _find_member(info, user_id=user_id, active_only=True)
    if not target:
        return error_response("Player not found in room", 404, "Player not found in room")
    if str(target.get("user_id")) != str(session["user_id"]) and not _can_manage_members(info):
        return error_response("Permission denied", 403, "Permission denied")

    data = request.get_json(silent=True) or {}
    character_card = data.get("character_card")
    if not _can_bind_character_card(character_card, target):
        return error_response("Permission denied", 403, "Permission denied")
    if not _bind_character(target, character_card):
        return error_response("Character card is required", 400, "Character card is required")
    _write_room(room_dir, info)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "绑定了房间角色卡"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        目标用户=user_id,
        角色卡ID=target.get("character_card", {}).get("id"),
        角色名=target.get("character_card", {}).get("name"),
    )
    return success_response(_room_summary(info), "Character bound successfully")


@bp.route("/api/rooms/<room_id>/members/<user_id>", methods=["DELETE"])
def delete_room_member(room_id, user_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_manage_members(info):
        return error_response("Permission denied", 403, "Permission denied")
    if str(user_id) == str(info.get("creator_id")):
        return error_response("Room owner cannot be removed", 400, "Room owner cannot be removed")

    target = _find_member(info, user_id=user_id, active_only=True)
    if not target:
        return error_response("Player not found in room", 404, "Player not found in room")
    target["status"] = ROOM_MEMBER_REMOVED
    target["is_active"] = False
    target["removed_at"] = _timestamp()
    if target.get("room_role") == ROOM_ROLE_ADMIN:
        target["room_role"] = ROOM_ROLE_MEMBER
    _write_room(room_dir, info)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "移除了房间成员"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        目标用户=user_id,
        房间名=info.get("name"),
    )
    return success_response(_room_summary(info), "Player removed")


@bp.route("/api/rooms/<room_id>/members/<user_id>/role", methods=["PUT"])
def update_room_member_role(room_id, user_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_manage_members(info):
        return error_response("Permission denied", 403, "Permission denied")
    if str(user_id) == str(info.get("creator_id")):
        return error_response("Room owner role cannot be changed", 400, "Room owner role cannot be changed")

    target = _find_member(info, user_id=user_id, active_only=True)
    if not target:
        return error_response("Player not found in room", 404, "Player not found in room")
    data = request.get_json(silent=True) or {}
    role = data.get("room_role")
    if role not in {ROOM_ROLE_ADMIN, ROOM_ROLE_MEMBER}:
        return error_response("Invalid room role", 400, "Invalid room role")
    target["room_role"] = role
    _write_room(room_dir, info)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "更改了房间成员权限"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        目标用户=user_id,
        权限=role,
    )
    return success_response(_room_summary(info), "Room role updated")


@bp.route("/api/rooms/<room_id>", methods=["GET"])
def get_room(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    data = _room_summary(info)
    data["messages"] = _read_messages(room_dir)
    return success_response(data, "Room loaded successfully")


@bp.route("/api/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_manage(info):
        return error_response("Permission denied", 403, "Permission denied")

    import shutil

    shutil.rmtree(room_dir)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "删除了房间"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        房间名=info.get("name"),
    )
    return success_response(message="Room deleted successfully")


@bp.route("/api/rooms/<room_id>/messages", methods=["GET"])
def get_room_messages(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    return success_response(_read_messages(room_dir), "Room messages loaded successfully")


@bp.route("/api/rooms/<room_id>/messages", methods=["POST"])
def create_room_message(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    data = request.get_json(silent=True) or {}
    content = str(data.get("content", "")).strip()
    if not content:
        return error_response("Please provide message content", 400, "No message content")

    member = _find_member(info, user_id=session["user_id"], active_only=True)
    if not member:
        return error_response("Permission denied", 403, "Permission denied")
    message = {
        "id": uuid4().hex,
        "type": data.get("type", "player"),
        "sender_id": member["user_id"],
        "sender_name": member["username"],
        "avatar": member["avatar"],
        "content": content,
        "time": data.get("time") or time.strftime("%H:%M"),
        "created_at": _timestamp(),
        "metadata": data.get("metadata", {}),
    }
    if message["type"] == "kp":
        message["sender_id"] = None
        message["sender_name"] = data.get("sender_name", "KP")
        message["avatar"] = "/assets/avatars/default_kp.jpg"
    elif message["type"] == "dice":
        message["sender_id"] = None
        message["sender_name"] = data.get("sender_name", "骰娘")
        message["avatar"] = "/assets/avatars/default_dice.jpg"
    elif message["type"] == "system":
        message["sender_id"] = None
        message["sender_name"] = data.get("sender_name", "系统")
        message["avatar"] = "/assets/avatars/default_system.jpg"

    messages = _read_messages(room_dir)
    messages.append(message)
    _write_messages(room_dir, messages)
    _write_room(room_dir, info)

    log_user_action(
        logger,
        user_action_text(session.get("username"), "发送了房间对话"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        消息类型=message["type"],
        内容长度=len(content),
    )
    return success_response(message, "Room message saved successfully", 201)


@bp.route("/api/rooms/<room_id>/character-records", methods=["POST"])
def create_character_record(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    return _create_character_record_for_room(room_dir, info)


def _create_character_record_for_room(room_dir, info):
    data = request.get_json(silent=True) or {}
    record_type = str(data.get("type", "")).strip().lower()
    if record_type not in {"damage", "san"}:
        return error_response("Invalid record type", 400, "Invalid record type")

    target = _find_member(info, user_id=data.get("user_id"), username=data.get("username"), active_only=True)
    if not target:
        return error_response("Player not found in room", 404, "Player not found in room")
    if not target.get("character_card"):
        return error_response("Player has no bound character card", 400, "No bound character card")

    value = _bounded_int(data.get("value"), 1, 999, 1)
    reason = str(data.get("reason") or "未知").strip() or "未知"
    state = _ensure_character_state(target)
    record = {
        "id": uuid4().hex,
        "type": record_type,
        "value": value,
        "reason": reason[:200],
        "created_at": _timestamp(),
        "created_by": session.get("user_id"),
        "created_by_name": session.get("username", "user"),
    }

    if record_type == "damage":
        state["current_hp"] = max(0, state["current_hp"] - value)
        record["hp_after"] = state["current_hp"]
        state["injury_records"].insert(0, record)
    else:
        state["current_san"] = max(0, state["current_san"] - value)
        record["san_after"] = state["current_san"]
        state["sanity_records"].insert(0, record)

    _write_room(room_dir, info)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "记录了角色状态变化"),
        用户ID=session.get("user_id"),
        房间ID=info.get("id"),
        类型=record_type,
        目标玩家=target.get("username"),
        数值=value,
        原因=reason,
    )
    return success_response({"member": target, "record": record}, "Character record created", 201)


@bp.route("/api/rooms/by-name/<path:room_name>/character-records", methods=["POST"])
def create_character_record_by_room_name(room_name):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room_by_name(room_name)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    return _create_character_record_for_room(room_dir, info)


@bp.route("/api/rooms/<room_id>/character-records/<record_id>", methods=["DELETE"])
def delete_character_record(room_id, record_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")
    if not _is_elevated():
        return error_response("Permission denied", 403, "Permission denied")

    for member in info.get("members", []):
        state = _ensure_character_state(member)
        for collection_name in ("injury_records", "sanity_records"):
            records = state.get(collection_name, [])
            next_records = [record for record in records if record.get("id") != record_id]
            if len(next_records) != len(records):
                state[collection_name] = next_records
                _recalculate_character_state(state)
                _write_room(room_dir, info)
                log_user_action(
                    logger,
                    user_action_text(session.get("username"), "删除了角色状态记录"),
                    用户ID=session.get("user_id"),
                    房间ID=room_id,
                    记录ID=record_id,
                )
                return success_response({"member": member}, "Character record deleted")

    return error_response("Record not found", 404, "Record not found")


@bp.route("/api/rooms/<room_id>/nodes", methods=["GET"])
def list_room_nodes(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    nodes_dir = room_dir / "nodes"
    nodes = []
    for node_file in nodes_dir.glob("*.json") if nodes_dir.exists() else []:
        node = read_json(node_file, default={})
        nodes.append(
            {
                "filename": node_file.name,
                "created_at": node.get("created_at", ""),
                "message_count": len(node.get("messages", [])),
            }
        )
    nodes.sort(key=lambda item: item["created_at"], reverse=True)
    return success_response({"info": _room_summary(info), "nodes": nodes}, "Room nodes loaded successfully")


@bp.route("/api/rooms/<room_id>/nodes", methods=["POST"])
def create_room_node(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    timestamp = int(time.time() * 1000)
    node = {
        "filename": f"{timestamp}.json",
        "created_at": _timestamp(),
        "messages": _read_messages(room_dir),
    }
    write_json_atomic(room_dir / "nodes" / node["filename"], node)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "创建了房间回档节点"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        文件=node["filename"],
    )
    return success_response(node, "Room node created successfully", 201)


@bp.route("/api/rooms/<room_id>/nodes/<node_filename>", methods=["GET"])
def get_room_node(room_id, node_filename):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    node_file = safe_join(room_dir / "nodes", node_filename)
    if not node_file.exists():
        return error_response("Room node not found", 404, "Room node not found")
    return success_response(read_json(node_file, default={}), "Room node loaded successfully")


@bp.route("/api/rooms/<room_id>/nodes/<node_filename>/restore", methods=["POST"])
def restore_room_node(room_id, node_filename):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    node_file = safe_join(room_dir / "nodes", node_filename)
    if not node_file.exists():
        return error_response("Room node not found", 404, "Room node not found")

    node = read_json(node_file, default={"messages": []})
    _write_messages(room_dir, node.get("messages", []))
    _write_room(room_dir, info)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "恢复了房间回档节点"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        文件=node_filename,
    )
    return success_response(node, "Room node restored successfully")


@bp.route("/api/rooms/<room_id>/nodes/<node_filename>", methods=["DELETE"])
def delete_room_node(room_id, node_filename):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_manage(info):
        return error_response("Permission denied", 403, "Permission denied")

    node_file = safe_join(room_dir / "nodes", node_filename)
    if node_file.exists():
        node_file.unlink()
    log_user_action(
        logger,
        user_action_text(session.get("username"), "删除了房间回档节点"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        文件=node_filename,
    )
    return success_response(message="Room node deleted successfully")


@bp.route("/api/rooms/<room_id>/autosave", methods=["POST"])
def save_room_autosave(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    autosave = {"updated_at": _timestamp(), "messages": _read_messages(room_dir)}
    write_json_atomic(room_dir / "autosave.json", autosave)
    log_user_action(
        logger,
        user_action_text(session.get("username"), "保存了房间自动存档"),
        用户ID=session.get("user_id"),
        房间ID=room_id,
        消息数=len(autosave["messages"]),
    )
    return success_response(autosave, "Room autosave saved successfully")


@bp.route("/api/rooms/<room_id>/autosave", methods=["GET"])
def load_room_autosave(room_id):
    login_error = _require_login()
    if login_error:
        return login_error

    room_dir, info = _find_room(room_id)
    if not room_dir:
        return error_response("Room not found", 404, "Room not found")
    if not _can_access(info):
        return error_response("Permission denied", 403, "Permission denied")

    autosave = read_json(room_dir / "autosave.json", default={"messages": []})
    return success_response(autosave, "Room autosave loaded successfully")
