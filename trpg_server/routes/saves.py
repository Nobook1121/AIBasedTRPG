import logging
import shutil
import time

from flask import Blueprint, current_app, jsonify, request

from trpg_server.json_store import read_json, write_json_atomic
from trpg_server.security import safe_join
from trpg_server.settings import SAVES_DIR

bp = Blueprint("saves", __name__)
logger = logging.getLogger(__name__)


def _get_saves_dir():
    return current_app.config.get("SAVES_DIR", SAVES_DIR)


def _timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _iter_save_dirs():
    saves_dir = _get_saves_dir()
    if not saves_dir.exists():
        return []
    return [path for path in saves_dir.iterdir() if path.is_dir()]


def _find_save_dir(save_id):
    for save_dir in _iter_save_dirs():
        info_file = save_dir / "info.json"
        if not info_file.exists():
            continue

        try:
            info = read_json(info_file, default={})
        except Exception:
            logger.exception("Failed to read save info: %s", info_file)
            continue

        if info.get("id") == save_id:
            return save_dir, info

    return None, None


@bp.route("/api/saves", methods=["GET"])
def get_saves_list():
    try:
        saves = []
        for save_dir in _iter_save_dirs():
            info_file = save_dir / "info.json"
            if not info_file.exists():
                continue
            try:
                saves.append(read_json(info_file, default={}))
            except Exception:
                logger.exception("Failed to read save info: %s", info_file)

        logger.info("Saves listed count=%s", len(saves))
        return jsonify(
            {
                "success": True,
                "data": saves,
                "message": "Saves loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to list saves")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load saves",
                }
            ),
            500,
        )


@bp.route("/api/saves", methods=["POST"])
def create_save():
    try:
        data = request.get_json(silent=True)
        if not data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide save data",
                    }
                ),
                400,
            )

        save_name = data.get("name", "").strip()
        scenario_id = data.get("scenario_id")
        scenario_title = data.get("scenario_title", "").strip()
        if not save_name:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Save name is required",
                        "message": "Please enter save name",
                    }
                ),
                400,
            )
        if scenario_id is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Scenario is required",
                        "message": "Please choose a scenario",
                    }
                ),
                400,
            )

        save_id = str(int(time.time() * 1000))
        save_dir = safe_join(_get_saves_dir(), save_name)
        if save_dir.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Save name already exists",
                        "message": "Please use another save name",
                    }
                ),
                400,
            )

        save_info = {
            "id": save_id,
            "name": save_name,
            "scenario_id": scenario_id,
            "scenario_title": scenario_title,
            "created_at": _timestamp(),
            "participants": [],
        }
        write_json_atomic(save_dir / "info.json", save_info)
        write_json_atomic(save_dir / "autosave.json", [])

        logger.info("Save created save_id=%s name=%s", save_id, save_name)
        return (
            jsonify(
                {
                    "success": True,
                    "data": save_info,
                    "message": "Save created successfully",
                }
            ),
            201,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc), "message": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to create save")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to create save",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>", methods=["DELETE"])
def delete_save(save_id):
    try:
        save_dir, _ = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        shutil.rmtree(save_dir)
        logger.info("Save deleted save_id=%s", save_id)
        return jsonify({"success": True, "message": "Save deleted successfully"})
    except Exception as exc:
        logger.exception("Failed to delete save: %s", save_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to delete save",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>/nodes", methods=["GET"])
def get_save_nodes(save_id):
    try:
        save_dir, save_info = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        nodes = []
        for node_file in save_dir.glob("*.json"):
            if node_file.name in {"info.json", "autosave.json"}:
                continue
            try:
                node_data = read_json(node_file, default={})
            except Exception:
                logger.exception("Failed to read save node: %s", node_file)
                continue

            nodes.append(
                {
                    "filename": node_file.name,
                    "created_at": node_data.get("created_at", ""),
                    "message_count": len(node_data.get("messages", [])),
                }
            )

        nodes.sort(key=lambda item: item["created_at"], reverse=True)
        return jsonify(
            {
                "success": True,
                "data": {"info": save_info, "nodes": nodes},
                "message": "Save nodes loaded successfully",
            }
        )
    except Exception as exc:
        logger.exception("Failed to list save nodes: %s", save_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load save nodes",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>/nodes", methods=["POST"])
def create_save_node(save_id):
    try:
        data = request.get_json(silent=True)
        if not data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide save data",
                    }
                ),
                400,
            )

        save_dir, _ = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        timestamp = int(time.time())
        node_data = {
            "created_at": _timestamp(),
            "timestamp": timestamp,
            "messages": data.get("messages", []),
        }
        write_json_atomic(save_dir / f"{timestamp}.json", node_data)

        logger.info(
            "Save node created save_id=%s message_count=%s",
            save_id,
            len(node_data["messages"]),
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": node_data,
                    "message": "Save node created successfully",
                }
            ),
            201,
        )
    except Exception as exc:
        logger.exception("Failed to create save node: %s", save_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to create save node",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>/nodes/<node_filename>", methods=["GET"])
def load_save_node(save_id, node_filename):
    try:
        save_dir, _ = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        node_file = safe_join(save_dir, node_filename)
        if not node_file.exists():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Save node not found",
                        "message": "Save node not found",
                    }
                ),
                404,
            )

        return jsonify(
            {
                "success": True,
                "data": read_json(node_file, default={}),
                "message": "Save node loaded successfully",
            }
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc), "message": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to load save node: %s %s", save_id, node_filename)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load save node",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>/nodes/<node_filename>", methods=["DELETE"])
def delete_save_node(save_id, node_filename):
    try:
        save_dir, _ = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        node_file = safe_join(save_dir, node_filename)
        if node_file.exists():
            node_file.unlink()

        logger.info("Save node deleted save_id=%s file=%s", save_id, node_filename)
        return jsonify({"success": True, "message": "Save node deleted successfully"})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc), "message": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to delete save node: %s %s", save_id, node_filename)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to delete save node",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>/autosave", methods=["POST"])
def save_autosave(save_id):
    try:
        data = request.get_json(silent=True)
        if not data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No data",
                        "message": "Please provide save data",
                    }
                ),
                400,
            )

        save_dir, _ = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        write_json_atomic(
            save_dir / "autosave.json",
            {"updated_at": _timestamp(), "messages": data.get("messages", [])},
        )
        return jsonify({"success": True, "message": "Autosave saved successfully"})
    except Exception as exc:
        logger.exception("Failed to save autosave: %s", save_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to save autosave",
                }
            ),
            500,
        )


@bp.route("/api/saves/<save_id>/autosave", methods=["GET"])
def load_autosave(save_id):
    try:
        save_dir, _ = _find_save_dir(save_id)
        if not save_dir:
            return _save_not_found()

        autosave_file = save_dir / "autosave.json"
        if autosave_file.exists():
            autosave_data = read_json(autosave_file, default={"messages": []})
            message = "Autosave loaded successfully"
        else:
            autosave_data = {"messages": []}
            message = "No autosave"

        return jsonify({"success": True, "data": autosave_data, "message": message})
    except Exception as exc:
        logger.exception("Failed to load autosave: %s", save_id)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(exc),
                    "message": "Failed to load autosave",
                }
            ),
            500,
        )


def _save_not_found():
    return (
        jsonify(
            {
                "success": False,
                "error": "Save not found",
                "message": "Save not found",
            }
        ),
        404,
    )
