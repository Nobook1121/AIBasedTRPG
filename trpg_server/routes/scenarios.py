import json
import logging
import time

from flask import Blueprint, jsonify

from trpg_server.settings import SCENARIOS_DIR

bp = Blueprint("scenarios", __name__)
logger = logging.getLogger(__name__)

_scenarios_cache = []
_cache_timestamp = 0
_cache_duration = 60


def load_scenarios():
    global _scenarios_cache, _cache_timestamp

    current_time = time.time()
    if current_time - _cache_timestamp < _cache_duration and _scenarios_cache:
        return _scenarios_cache

    scenarios = []
    if not SCENARIOS_DIR.exists():
        return scenarios

    for path in SCENARIOS_DIR.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as file:
                scenario = json.load(file)
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


@bp.route("/api/scenarios/list", methods=["GET"])
def get_scenario_list():
    try:
        files = []
        if SCENARIOS_DIR.exists():
            for path in SCENARIOS_DIR.glob("*.json"):
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
