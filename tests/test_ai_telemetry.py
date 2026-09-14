import json

from trpg_server.agents.telemetry import (
    build_provider_cache_key,
    calculate_cache_hit_rate,
    load_daily_ai_usage,
    record_ai_usage,
)


def test_cache_key_is_stable_and_does_not_include_room():
    first = build_provider_cache_key("scenario", "1", "scene", "2", "rules")
    second = build_provider_cache_key("scenario", "1", "scene", "2", "rules")
    assert first == second
    assert "room" not in first


def test_cache_hit_rate_is_clamped():
    assert calculate_cache_hit_rate(100, 25) == 25.0
    assert calculate_cache_hit_rate(0, 10) == 0.0
    assert calculate_cache_hit_rate(100, 200) == 100.0


def test_daily_usage_aggregates_arbitrary_agent_roles(tmp_path):
    record_ai_usage(tmp_path, {"agent_id": "kp", "total_tokens": 10, "prompt_tokens": 8, "completion_tokens": 2})
    record_ai_usage(tmp_path, {"agent_id": "future_role", "total_tokens": 7, "prompt_tokens": 5, "completion_tokens": 2})

    report = load_daily_ai_usage(tmp_path)
    assert report["total_tokens"] == 17
    assert report["roles"]["kp"]["total_tokens"] == 10
    assert report["roles"]["future_role"]["total_tokens"] == 7
    first_line = (tmp_path / "ai_usage.jsonl").read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(first_line)["agent_id"] == "kp"


def test_daily_usage_reports_prefix_rate_scenario_distribution_and_room_costs(tmp_path):
    record_ai_usage(tmp_path, {"agent_id": "kp", "scenario_id": "s1", "room_id": "r1", "prompt_tokens": 100, "completion_tokens": 10, "cached_tokens": 80, "prefix_cache_hit": True})
    report = load_daily_ai_usage(tmp_path)
    assert report["prefix_cache_hit_rate"] == 100.0
    assert report["scenario_distribution"] == {"s1": 1}
    assert report["room_costs"]["r1"]["total_tokens"] == 110
