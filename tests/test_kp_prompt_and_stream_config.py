from pathlib import Path


def test_kp_prompt_is_valid_chinese_and_requires_tools_for_dice():
    prompt = Path("data/config/roles/kp.md").read_text(encoding="utf-8")

    assert "浣犳槸" not in prompt
    assert "你是KP" in prompt
    assert "COC7" in prompt
    assert "不得编造骰点" in prompt
    assert "dice.roll_coc_check" in prompt
    assert "不无故让调查员死亡" in prompt
    assert "失败归因" in prompt
