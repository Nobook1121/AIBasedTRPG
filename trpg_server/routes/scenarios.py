import json
import logging
import time
from pathlib import Path
from urllib.parse import unquote

from flask import Blueprint, request, session

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.logging_config import log_user_action, user_action_text
from trpg_server.responses import error_response, success_response
from trpg_server.security import (
    build_public_asset_url,
    is_allowed_upload,
    normalize_filename,
    safe_join,
)
from trpg_server.settings import SCENARIO_COVERS_DIR, SCENARIOS_DIR

bp = Blueprint("scenarios", __name__)
logger = logging.getLogger(__name__)

_scenarios_cache = []
_cache_timestamp = 0
_cache_duration = 60
_allowed_cover_extensions = {"png", "jpg", "jpeg", "gif"}
_elevated_roles = {"OWNER", "ADMIN"}


def clear_scenarios_cache():
    global _scenarios_cache, _cache_timestamp

    _scenarios_cache = []
    _cache_timestamp = 0


def _current_timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"


def _scenario_filename(title):
    return normalize_filename(f"{title or 'unnamed'}.json")


def _cover_filename(value):
    return normalize_filename(unquote(str(value or "")))


def _require_login():
    if "user_id" not in session:
        return error_response("Please login first", 401, "Not logged in")
    return None


def _can_modify_scenario(scenario):
    if session.get("role") in _elevated_roles:
        return True
    return scenario.get("owner_id") == session.get("user_id")


def _iter_scenario_files():
    if not SCENARIOS_DIR.exists():
        return []
    return list(SCENARIOS_DIR.glob("*.json"))


def _find_scenario_file(scenario_id):
    for path in _iter_scenario_files():
        try:
            data = read_json(path, default={})
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to read scenario file: %s", path.name)
            continue

        if data.get("id") == scenario_id or str(data.get("id")) == str(scenario_id):
            return path, data

    return None, None


def load_scenarios():
    global _scenarios_cache, _cache_timestamp

    current_time = time.time()
    if current_time - _cache_timestamp < _cache_duration and _scenarios_cache:
        return _scenarios_cache

    scenarios = []
    for path in _iter_scenario_files():
        try:
            scenario = read_json(path, default={})
        except json.JSONDecodeError:
            logger.exception("Failed to parse scenario file: %s", path.name)
            continue
        except OSError:
            logger.exception("Failed to read scenario file: %s", path.name)
            continue

        if "id" not in scenario:
            try:
                scenario["id"] = int(path.stem.split("_")[-1])
            except (ValueError, IndexError):
                scenario["id"] = int(time.time() * 1000)
        scenarios.append(scenario)

    _scenarios_cache = scenarios
    _cache_timestamp = current_time
    return scenarios


@bp.route("/api/scenarios", methods=["GET"])
def get_all_scenarios():
    try:
        scenarios = load_scenarios()
        return success_response(
            scenarios,
            f"Successfully loaded {len(scenarios)} scenarios",
        )
    except Exception as exc:
        logger.exception("Failed to load scenarios")
        return error_response("Failed to load scenarios", 500, str(exc))


@bp.route("/api/scenarios/<int:scenario_id>", methods=["GET"])
def get_scenario(scenario_id):
    try:
        scenario = next(
            (item for item in load_scenarios() if item.get("id") == scenario_id),
            None,
        )
        if scenario is None:
            return error_response("Scenario not found", 404, "Scenario not found")

        return success_response(scenario, "Scenario loaded successfully")
    except Exception as exc:
        logger.exception("Failed to load scenario: %s", scenario_id)
        return error_response("Failed to load scenario", 500, str(exc))


@bp.route("/api/scenarios", methods=["POST"])
def create_scenario():
    try:
        login_error = _require_login()
        if login_error:
            return login_error

        scenario_data = request.get_json(silent=True)
        if not scenario_data:
            return error_response("Please provide scenario data", 400, "No data")

        title = scenario_data.get("title", "unnamed")
        for path in _iter_scenario_files():
            try:
                existing_data = read_json(path, default={})
            except (json.JSONDecodeError, OSError):
                logger.exception("Failed to check scenario title: %s", path.name)
                continue

            if existing_data.get("title") == title:
                return error_response(
                    f'Scenario title "{title}" already exists',
                    400,
                    "Scenario title already exists",
                )

        scenario_id = int(time.time() * 1000)
        scenario_data["id"] = scenario_id
        scenario_data["owner_id"] = session["user_id"]
        scenario_data["createdAt"] = _current_timestamp()
        if not scenario_data.get("cover"):
            scenario_data["cover"] = "/assets/scenario_covers/default_cover.png"

        filename = _scenario_filename(title)
        file_path = safe_join(SCENARIOS_DIR, filename)
        write_json_atomic(file_path, scenario_data)
        clear_scenarios_cache()

        log_user_action(
            logger,
            user_action_text(session.get("username"), "创建了剧本"),
            用户ID=session.get("user_id"),
            剧本ID=scenario_id,
            标题=title,
        )
        return success_response(
            scenario_data,
            "Scenario created successfully",
            201,
        )
    except Exception as exc:
        logger.exception("Failed to create scenario")
        return error_response("Failed to create scenario", 500, str(exc))


@bp.route("/api/scenarios/<int:scenario_id>", methods=["PUT"])
def update_scenario(scenario_id):
    try:
        login_error = _require_login()
        if login_error:
            return login_error

        scenario_data = request.get_json(silent=True)
        if not scenario_data:
            return error_response("Please provide scenario data", 400, "No data")

        target_file, existing_scenario = _find_scenario_file(scenario_id)
        if target_file is None:
            return error_response(
                f"Scenario with ID {scenario_id} does not exist",
                404,
                "Scenario not found",
            )

        if not _can_modify_scenario(existing_scenario):
            return error_response("Permission denied", 403, "Permission denied")

        scenario_data["id"] = scenario_id
        scenario_data["owner_id"] = existing_scenario.get("owner_id")
        scenario_data["updatedAt"] = _current_timestamp()
        if "createdAt" not in scenario_data:
            scenario_data["createdAt"] = existing_scenario.get(
                "createdAt",
                _current_timestamp(),
            )

        write_json_atomic(target_file, scenario_data)
        clear_scenarios_cache()

        log_user_action(
            logger,
            user_action_text(session.get("username"), "更新了剧本"),
            用户ID=session.get("user_id"),
            剧本ID=scenario_id,
            标题=scenario_data.get("title", "unknown"),
        )
        return success_response(scenario_data, "Scenario updated successfully")
    except Exception as exc:
        logger.exception("Failed to update scenario: %s", scenario_id)
        return error_response("Failed to update scenario", 500, str(exc))


@bp.route("/api/scenarios/<int:scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id):
    try:
        login_error = _require_login()
        if login_error:
            return login_error

        user_id = "unknown"
        request_data = request.get_json(silent=True)
        if request_data:
            user_id = request_data.get("user_id", "unknown")

        target_file, scenario_data = _find_scenario_file(scenario_id)
        if target_file is None:
            return error_response(
                f"Scenario with ID {scenario_id} does not exist",
                404,
                "Scenario not found",
            )

        if not _can_modify_scenario(scenario_data):
            return error_response("Permission denied", 403, "Permission denied")

        target_file.unlink()
        cover_path = safe_join(SCENARIO_COVERS_DIR, f"{scenario_id}.png")
        if cover_path.exists():
            cover_path.unlink()

        clear_scenarios_cache()
        log_user_action(
            logger,
            user_action_text(session.get("username"), "删除了剧本"),
            用户ID=session.get("user_id") or user_id,
            剧本ID=scenario_id,
            标题=scenario_data.get("title", "unknown"),
        )
        return success_response(message="Scenario deleted successfully")
    except Exception as exc:
        logger.exception("Failed to delete scenario: %s", scenario_id)
        return error_response("Failed to delete scenario", 500, str(exc))


@bp.route("/api/scenarios/cover", methods=["POST"])
def upload_scenario_cover():
    try:
        login_error = _require_login()
        if login_error:
            return login_error

        user_id = session.get("user_id") or request.form.get("user_id", "unknown")
        if "cover" not in request.files:
            return error_response(
                "Please choose a scenario cover image",
                400,
                "No file",
            )

        cover = request.files["cover"]
        if not is_allowed_upload(cover.filename or "", _allowed_cover_extensions):
            return error_response(
                "Please upload an image file",
                400,
                "Invalid file type",
            )

        if (cover.content_length or 0) > 5 * 1024 * 1024:
            return error_response(
                "Cover file size must not exceed 5MB",
                400,
                "File too large",
            )

        scenario_title = request.form.get("scenario_title", str(int(time.time() * 1000)))
        filename = normalize_filename(f"{scenario_title}.png")
        file_path = safe_join(SCENARIO_COVERS_DIR, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists():
            file_path.unlink()

        cover.save(file_path)
        cover_url = build_public_asset_url("/assets/scenario_covers", filename)

        log_user_action(
            logger,
            user_action_text(session.get("username"), "上传了剧本封面"),
            用户ID=user_id,
            文件=filename,
            剧本标题=scenario_title,
        )
        return success_response(
            {"cover_url": cover_url},
            "Cover uploaded successfully",
        )
    except Exception as exc:
        logger.exception("Failed to upload scenario cover")
        return error_response("Failed to upload cover", 500, str(exc))


@bp.route("/api/scenarios/cover", methods=["DELETE"])
def delete_scenario_cover():
    try:
        login_error = _require_login()
        if login_error:
            return login_error

        user_id = session.get("user_id", "unknown")
        data = request.get_json(silent=True)
        if not data or "cover_path" not in data:
            return error_response("Please provide cover path", 400, "No data")

        filename = _cover_filename(Path(data["cover_path"]).name)
        if filename == "default_cover.png":
            return error_response(
                "Default cover cannot be deleted",
                400,
                "Default cover cannot be deleted",
            )

        file_path = safe_join(SCENARIO_COVERS_DIR, filename)
        if not file_path.exists():
            return error_response("Cover file does not exist", 404, "File not found")

        file_path.unlink()
        log_user_action(
            logger,
            user_action_text(session.get("username"), "删除了剧本封面"),
            用户ID=user_id,
            文件=filename,
        )
        return success_response(message="Cover deleted successfully")
    except Exception as exc:
        logger.exception("Failed to delete scenario cover")
        return error_response("Failed to delete cover", 500, str(exc))


@bp.route("/api/scenarios/cover/rename", methods=["POST"])
def rename_scenario_cover():
    try:
        login_error = _require_login()
        if login_error:
            return login_error

        user_id = session.get("user_id", "unknown")
        data = request.get_json(silent=True)
        if not data or "old_filename" not in data or "new_filename" not in data:
            return error_response(
                "Please provide old and new filenames",
                400,
                "No data",
            )

        old_filename = _cover_filename(Path(data["old_filename"]).name)
        new_filename = _cover_filename(Path(data["new_filename"]).name)
        if old_filename == "default_cover.png":
            return error_response(
                "Default cover cannot be renamed",
                400,
                "Default cover cannot be renamed",
            )

        old_file_path = safe_join(SCENARIO_COVERS_DIR, old_filename)
        new_file_path = safe_join(SCENARIO_COVERS_DIR, new_filename)
        if not old_file_path.exists():
            return error_response("Cover file does not exist", 404, "File not found")

        if new_file_path.exists():
            new_file_path.unlink()
        old_file_path.rename(new_file_path)

        log_user_action(
            logger,
            user_action_text(session.get("username"), "重命名了剧本封面"),
            用户ID=user_id,
            原文件=old_filename,
            新文件=new_filename,
        )
        return success_response(message="Cover renamed successfully")
    except Exception as exc:
        logger.exception("Failed to rename scenario cover")
        return error_response("Failed to rename cover", 500, str(exc))


@bp.route("/api/scenarios/list", methods=["GET"])
def get_scenario_list():
    try:
        files = []
        for path in _iter_scenario_files():
            try:
                stat = path.stat()
            except OSError:
                logger.exception("Failed to stat scenario file: %s", path.name)
                continue

            files.append(
                {
                    "filename": path.name,
                    "size": stat.st_size,
                    "mtime": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)
                    ),
                }
            )

        return success_response(
            {"files": files, "total": len(files)},
            "Scenario list loaded successfully",
        )
    except Exception as exc:
        logger.exception("Failed to list scenario files")
        return error_response("Failed to list scenario files", 500, str(exc))
