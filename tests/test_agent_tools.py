from trpg_server.agents.tools.dice import roll_coc_check


def test_coc_check_regular_success_with_fixed_rng():
    result = roll_coc_check(
        {
            "skill": "锁匠",
            "target": 45,
            "difficulty": "regular",
            "reason": "打开地下室门锁",
        },
        rng=lambda sides: 34,
    )

    assert result["roll"] == 34
    assert result["target"] == 45
    assert result["threshold"] == 45
    assert result["success"] is True
    assert result["success_level"] == "regular"
    assert "锁匠" in result["summary"]


def test_coc_check_hard_failure_uses_half_threshold():
    result = roll_coc_check(
        {"skill": "侦查", "target": 50, "difficulty": "hard"},
        rng=lambda sides: 31,
    )

    assert result["threshold"] == 25
    assert result["success"] is False
    assert result["success_level"] == "failure"


def test_coc_check_extreme_success_uses_fifth_threshold():
    result = roll_coc_check(
        {"skill": "图书馆使用", "target": 80, "difficulty": "extreme"},
        rng=lambda sides: 16,
    )

    assert result["threshold"] == 16
    assert result["success"] is True
    assert result["success_level"] == "extreme"


def test_coc_check_rejects_invalid_target():
    result = roll_coc_check({"skill": "锁匠", "target": 0}, rng=lambda sides: 1)

    assert result["error"] == "target must be between 1 and 100"
