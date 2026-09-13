from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any


USAGE_FILENAME = "ai_usage.jsonl"


def calculate_cache_hit_rate(prompt_tokens: int | float | None, cached_tokens: int | float | None) -> float:
    prompt = max(0.0, float(prompt_tokens or 0))
    cached = max(0.0, min(prompt, float(cached_tokens or 0)))
    return round((cached / prompt) * 100, 2) if prompt else 0.0


def build_provider_cache_key(
    scenario_id: Any,
    scenario_version: Any,
    scene_id: Any,
    scene_version: Any,
    rules_version: Any,
) -> str:
    return (
        f"scenario:{scenario_id}@{scenario_version}:"
        f"scene:{scene_id}@{scene_version}:rules:{rules_version}"
    )


def _usage_path(log_dir: Path) -> Path:
    return Path(log_dir) / USAGE_FILENAME


def record_ai_usage(log_dir: Path, usage: dict[str, Any]) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    item = {str(key): value for key, value in usage.items()}
    item.setdefault("timestamp", now)
    item.setdefault("day", item["timestamp"][:10])
    item.setdefault("agent_id", "unknown")
    item.setdefault("prompt_tokens", 0)
    item.setdefault("completion_tokens", 0)
    item.setdefault("total_tokens", int(item["prompt_tokens"] or 0) + int(item["completion_tokens"] or 0))
    item.setdefault("cached_tokens", 0)
    item["prefix_cache_hit"] = bool(item.get("prefix_cache_hit", False))
    item.setdefault("prefix_cache_requests", 1)
    item.setdefault("prefix_cache_hits", int(item["prefix_cache_hit"]))
    item["cache_hit_rate"] = calculate_cache_hit_rate(item["prompt_tokens"], item["cached_tokens"])
    path = _usage_path(Path(log_dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    return item


def load_daily_ai_usage(log_dir: Path, day: str | None = None) -> dict[str, Any]:
    target_day = day or date.today().isoformat()
    roles: dict[str, dict[str, Any]] = {}
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "prefix_cache_hits": 0,
        "prefix_cache_requests": 0,
    }
    path = _usage_path(Path(log_dir))
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict) or str(item.get("day") or str(item.get("timestamp", ""))[:10]) != target_day:
                continue
            agent_id = str(item.get("agent_id") or "unknown")
            bucket = roles.setdefault(
                agent_id,
                {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cached_tokens": 0,
                    "prefix_cache_hits": 0,
                    "prefix_cache_requests": 0,
                    "request_count": 0,
                },
            )
            for key in totals:
                value = item.get(key)
                if key == "prefix_cache_hits" and value is None:
                    value = int(bool(item.get("prefix_cache_hit", False)))
                if key == "prefix_cache_requests" and value is None:
                    value = 1
                bucket[key] += int(value or 0)
                totals[key] += int(value or 0)
            bucket["request_count"] += 1
    for bucket in roles.values():
        bucket["cache_hit_rate"] = calculate_cache_hit_rate(bucket["prompt_tokens"], bucket["cached_tokens"])
        bucket["prefix_cache_hit_rate"] = round(
            (bucket["prefix_cache_hits"] / bucket["prefix_cache_requests"]) * 100,
            2,
        ) if bucket["prefix_cache_requests"] else 0.0
    totals["cache_hit_rate"] = calculate_cache_hit_rate(totals["prompt_tokens"], totals["cached_tokens"])
    totals["prefix_cache_hit_rate"] = round(
        (totals["prefix_cache_hits"] / totals["prefix_cache_requests"]) * 100,
        2,
    ) if totals["prefix_cache_requests"] else 0.0
    return {"day": target_day, **totals, "roles": roles}


def load_room_ai_usage(log_dir: Path, room_id: Any) -> dict[str, Any]:
    """Aggregate token usage recorded for one room across all days."""
    target = str(room_id or "")
    result = {"room_id": target, "request_count": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cached_tokens": 0}
    if not target:
        return result
    path = _usage_path(Path(log_dir))
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict) or str(item.get("room_id") or "") != target:
            continue
        result["request_count"] += 1
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens"):
            result[key] += int(item.get(key) or 0)
    result["cache_hit_rate"] = calculate_cache_hit_rate(result["prompt_tokens"], result["cached_tokens"])
    return result


def load_ai_usage_history(log_dir: Path, days: int = 30) -> list[dict[str, Any]]:
    """Return daily role buckets for a bounded recent window."""
    days = max(1, min(int(days or 30), 365))
    from datetime import date, timedelta
    start = date.today() - timedelta(days=days - 1)
    return [load_daily_ai_usage(log_dir, (start + timedelta(days=index)).isoformat()) for index in range(days)]
