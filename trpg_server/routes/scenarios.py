import json
import logging
import time
from pathlib import Path

from flask import Blueprint, jsonify, request, session

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.security import is_allowed_upload, safe_join
from trpg_server.settings import SCENARIO_COVERS_DIR, SCENARIOS_DIR

bp = Blueprint("scenarios", __name__)
logger = logging.getLogger(__name__)

_scenarios_cache = []
_cache_timestamp = 0
_cache_duration = 60
_allowed_cover_extensions = {"png", "jpg", "jpeg", "gif"}


def clear_scenarios_cache():
    global _scenarios_cache, _cache_timestamp

    _scenarios_cache = []
    _cache_timestamp = 0


def _current_timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"


def _scenario_filename(title):
    safe_title = str(title or "unnamed").replace("/", "_").replace("\\", "_")
    return f"{safe_title}.json"


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
        return jsonify(
            {
                "success": True,
                "data": scenarios,
                "message": f"Successfully loaded {len(scenarios)} scenarios",
            }
        )
    except Exception as exc:
        logger.exception("Failed to load scenarios")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load scenarios",
                }
            ),
            500,
        )


@bp.route("/api/scenarios/<int:scenario_id>", methods=["GET"])
def get_scenario(scenario_id):
    try:
        scenario = next(
            (item for item in load_scenarios() if item.get("id") == scenario_id),
            None,
        )
        if scenario is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Scenario not found",
                        "message": "Scenario not found",
                    }
                ),
                404,
            )

        return jsonify(
            {
                "success": True,
                "data": scenario,
                "message": "Scenario loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to load scenario: %s", scenario_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load scenario",
                }
            ),
            500,
        )


@bp.route("/api/scenarios", methods=["POST"])
def create_scenario():
    try:
        scenario_data = request.get_json(silent=True)
        if not scenario_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide scenario data",
                    }
                ),
                400,
            )

        title = scenario_data.get("title", "unnamed")
        for path in _iter_scenario_files():
            try:
                existing_data = read_json(path, default={})
            except (json.JSONDecodeError, OSError):
                logger.exception("Failed to check scenario title: %s", path.name)
                continue

            if existing_data.get("title") == title:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Scenario title already exists",
                            "message": f'Scenario title "{title}" already exists',
                        }
                    ),
                    400,
                )

        scenario_id = int(time.time() * 1000)
        scenario_data["id"] = scenario_id
        scenario_data["createdAt"] = _current_timestamp()
        if not scenario_data.get("cover"):
            scenario_data["cover"] = "/scenario_covers/default_cover.png"

        filename = _scenario_filename(title)
        file_path = safe_join(SCENARIOS_DIR, filename)
        write_json_atomic(file_path, scenario_data)
        clear_scenarios_cache()

        logger.info(
            "Scenario created user_id=%s scenario_id=%s title=%s",
            scenario_data.get("user_id", "unknown"),
            scenario_id,
            title,
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": scenario_data,
                    "message": "Scenario created successfully",
                }
            ),
            201,
        )
    except Exception as exc:
        logger.exception("Failed to create scenario")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to create scenario",
                }
            ),
            500,
        )


@bp.route("/api/scenarios/<int:scenario_id>", methods=["PUT"])
def update_scenario(scenario_id):
    try:
        scenario_data = request.get_json(silent=True)
        if not scenario_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide scenario data",
                    }
                ),
                400,
            )

        target_file, existing_scenario = _find_scenario_file(scenario_id)
        if target_file is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Scenario not found",
                        "message": f"Scenario with ID {scenario_id} does not exist",
                    }
                ),
                404,
            )

        scenario_data["id"] = scenario_id
        scenario_data["updatedAt"] = _current_timestamp()
        if "createdAt" not in scenario_data:
            scenario_data["createdAt"] = existing_scenario.get(
                "createdAt",
                _current_timestamp(),
            )

        write_json_atomic(target_file, scenario_data)
        clear_scenarios_cache()

        logger.info(
            "Scenario updated user_id=%s scenario_id=%s title=%s",
            scenario_data.get("user_id", "unknown"),
            scenario_id,
            scenario_data.get("title", "unknown"),
        )
        return jsonify(
            {
                "success": True,
                "data": scenario_data,
                "message": "Scenario updated successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to update scenario: %s", scenario_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to update scenario",
                }
            ),
            500,
        )


@bp.route("/api/scenarios/<int:scenario_id>", methods=["DELETE"])
def delete_scenario(scenario_id):
    try:
        user_id = "unknown"
        request_data = request.get_json(silent=True)
        if request_data:
            user_id = request_data.get("user_id", "unknown")

        target_file, scenario_data = _find_scenario_file(scenario_id)
        if target_file is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Scenario not found",
                        "message": f"Scenario with ID {scenario_id} does not exist",
                    }
                ),
                404,
            )

        target_file.unlink()
        cover_path = safe_join(SCENARIO_COVERS_DIR, f"{scenario_id}.png")
        if cover_path.exists():
            cover_path.unlink()

        clear_scenarios_cache()
        logger.info(
            "Scenario deleted user_id=%s scenario_id=%s title=%s",
            user_id,
            scenario_id,
            scenario_data.get("title", "unknown"),
        )
        return jsonify(
            {
                "success": True,
                "message": "Scenario deleted successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to delete scenario: %s", scenario_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to delete scenario",
                }
            ),
            500,
        )


@bp.route("/api/scenarios/cover", methods=["POST"])
def upload_scenario_cover():
    try:
        user_id = session.get("user_id") or request.form.get("user_id", "unknown")
        if "cover" not in request.files:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No file",
                        "message": "Please choose a scenario cover image",
                    }
                ),
                400,
            )

        cover = request.files["cover"]
        if not is_allowed_upload(cover.filename or "", _allowed_cover_extensions):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid file type",
                        "message": "Please upload an image file",
                    }
                ),
                400,
            )

        if (cover.content_length or 0) > 5 * 1024 * 1024:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "File too large",
                        "message": "Cover file size must not exceed 5MB",
                    }
                ),
                400,
            )

        scenario_title = request.form.get("scenario_title", str(int(time.time() * 1000)))
        safe_title = scenario_title.replace("/", "_").replace("\\", "_")
        filename = f"{safe_title}.png"
        file_path = safe_join(SCENARIO_COVERS_DIR, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists():
            file_path.unlink()

        cover.save(file_path)
        cover_url = f"/assets/scenario_covers/{filename}"

        logger.info("Scenario cover uploaded user_id=%s file=%s", user_id, filename)
        return jsonify(
            {
                "success": True,
                "data": {"cover_url": cover_url},
                "message": "Cover uploaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to upload scenario cover")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to upload cover",
                }
            ),
            500,
        )


@bp.route("/api/scenarios/cover", methods=["DELETE"])
def delete_scenario_cover():
    try:
        user_id = session.get("user_id", "unknown")
        data = request.get_json(silent=True)
        if not data or "cover_path" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide cover path",
                    }
                ),
                400,
            )

        filename = Path(data["cover_path"]).name
        if filename == "default_cover.png":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Default cover cannot be deleted",
                        "message": "Default cover cannot be deleted",
                    }
                ),
                400,
            )

        file_path = safe_join(SCENARIO_COVERS_DIR, filename)
        if not file_path.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "File not found",
                        "message": "Cover file does not exist",
                    }
                ),
                404,
            )

        file_path.unlink()
        logger.info("Scenario cover deleted user_id=%s file=%s", user_id, filename)
        return jsonify(
            {
                "success": True,
                "message": "Cover deleted successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to delete scenario cover")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to delete cover",
                }
            ),
            500,
        )


@bp.route("/api/scenarios/cover/rename", methods=["POST"])
def rename_scenario_cover():
    try:
        user_id = session.get("user_id", "unknown")
        data = request.get_json(silent=True)
        if not data or "old_filename" not in data or "new_filename" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide old and new filenames",
                    }
                ),
                400,
            )

        old_filename = Path(data["old_filename"]).name
        new_filename = Path(data["new_filename"]).name
        if old_filename == "default_cover.png":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Default cover cannot be renamed",
                        "message": "Default cover cannot be renamed",
                    }
                ),
                400,
            )

        old_file_path = safe_join(SCENARIO_COVERS_DIR, old_filename)
        new_file_path = safe_join(SCENARIO_COVERS_DIR, new_filename)
        if not old_file_path.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "File not found",
                        "message": "Cover file does not exist",
                    }
                ),
                404,
            )

        if new_file_path.exists():
            new_file_path.unlink()
        old_file_path.rename(new_file_path)

        logger.info(
            "Scenario cover renamed user_id=%s old_file=%s new_file=%s",
            user_id,
            old_filename,
            new_filename,
        )
        return jsonify(
            {
                "success": True,
                "message": "Cover renamed successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to rename scenario cover")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to rename cover",
                }
            ),
            500,
        )


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

        return jsonify(
            {
                "success": True,
                "data": {"files": files, "total": len(files)},
                "message": "Scenario list loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to list scenario files")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to list scenario files",
                }
            ),
            500,
        )
