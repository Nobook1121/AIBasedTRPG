import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AIRuntimeConfig:
    stream_output: bool = False
    debug_mode: bool = False
    show_ai_hints: bool = True
    small_model_tasks: dict[str, str] = field(default_factory=lambda: {
        "intent_classification": "",
        "state_update": "",
        "summarization": "",
        "schema_repair": "",
    })
    # Prompt-compaction knobs. These bound how much *redundant* context is sent
    # to the model without capping tool-call rounds or the response max_tokens.
    snapshot_manifest_summary_cap: int = 140
    max_snapshot_scene_manifest: int = 30
    snapshot_include_entity_manifest: bool = False
    max_tool_result_chars: int = 4000
    # KP 单次发言允许的最大工具调用轮数，以及每次 AI 请求的等待时间（秒）。
    # 超过后不会静默丢回复，而是给出明确的收尾叙事与提示。
    max_tool_rounds: int = 8
    ai_request_timeout: int = 300
    # 骰娘大成功 / 大失败的全局默认阈值（管理员设置页可改，房规可覆盖）。
    dice_critical_threshold: int = 1
    dice_fumble_threshold: int = 96


def _toml_int(value: str, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _unquote_toml_name(raw: str) -> str:
    """去掉段名 / 键名外层引号（如 `["ai.small_models"]` 中的引号）。

    手写解析器按行切分，若不还原引号，点号段名（``ai.small_models``）会永远匹配不上。
    """
    text = raw.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            unquoted = json.loads(text)
        except ValueError:
            return text
        return unquoted if isinstance(unquoted, str) else text
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]
    return text


def load_ai_runtime_config(config_dir: Path) -> AIRuntimeConfig:
    general_file = Path(config_dir) / "general.toml"
    if not general_file.exists():
        return AIRuntimeConfig()

    current_section = ""
    stream_output = False
    debug_mode = False
    show_ai_hints = True
    small_model_tasks = AIRuntimeConfig().small_model_tasks.copy()
    snapshot_manifest_summary_cap = AIRuntimeConfig.snapshot_manifest_summary_cap
    max_snapshot_scene_manifest = AIRuntimeConfig.max_snapshot_scene_manifest
    snapshot_include_entity_manifest = AIRuntimeConfig.snapshot_include_entity_manifest
    max_tool_result_chars = AIRuntimeConfig.max_tool_result_chars
    max_tool_rounds = AIRuntimeConfig.max_tool_rounds
    ai_request_timeout = AIRuntimeConfig.ai_request_timeout
    dice_critical_threshold = AIRuntimeConfig.dice_critical_threshold
    dice_fumble_threshold = AIRuntimeConfig.dice_fumble_threshold
    for raw_line in general_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = _unquote_toml_name(line[1:-1])
            continue
        if current_section in {"ai", "ai.small_models", "ai.prompt"} and "=" in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            key = _unquote_toml_name(key)
            quoted_value = bool(value.startswith(('"', "'")))
            if quoted_value and value.endswith(('"', "'")):
                value = value[1:-1]
            if current_section == "ai.small_models":
                small_model_tasks[key] = value
            elif current_section == "ai.prompt":
                if key == "snapshot_manifest_summary_cap":
                    snapshot_manifest_summary_cap = max(0, _toml_int(value, AIRuntimeConfig.snapshot_manifest_summary_cap))
                elif key == "max_snapshot_scene_manifest":
                    max_snapshot_scene_manifest = max(0, _toml_int(value, AIRuntimeConfig.max_snapshot_scene_manifest))
                elif key == "snapshot_include_entity_manifest":
                    snapshot_include_entity_manifest = value.lower() == "true"
                elif key == "max_tool_result_chars":
                    max_tool_result_chars = max(500, _toml_int(value, AIRuntimeConfig.max_tool_result_chars))
            elif key == "stream_output":
                stream_output = value.lower() == "true"
            elif key == "debug_mode":
                debug_mode = value.lower() == "true"
            elif key in {"show_ai_hints", "show_kp_hints", "reply_hints"}:
                show_ai_hints = value.lower() == "true"
            elif key == "max_tool_rounds":
                max_tool_rounds = max(1, min(30, _toml_int(value, AIRuntimeConfig.max_tool_rounds)))
            elif key == "ai_request_timeout":
                ai_request_timeout = max(30, min(1800, _toml_int(value, AIRuntimeConfig.ai_request_timeout)))
            elif key == "dice_critical_threshold":
                dice_critical_threshold = max(0, min(100, _toml_int(value, AIRuntimeConfig.dice_critical_threshold)))
            elif key == "dice_fumble_threshold":
                dice_fumble_threshold = max(0, min(100, _toml_int(value, AIRuntimeConfig.dice_fumble_threshold)))
    return AIRuntimeConfig(
        stream_output=stream_output,
        debug_mode=debug_mode,
        show_ai_hints=show_ai_hints,
        small_model_tasks=small_model_tasks,
        snapshot_manifest_summary_cap=snapshot_manifest_summary_cap,
        max_snapshot_scene_manifest=max_snapshot_scene_manifest,
        snapshot_include_entity_manifest=snapshot_include_entity_manifest,
        max_tool_result_chars=max_tool_result_chars,
        max_tool_rounds=max_tool_rounds,
        ai_request_timeout=ai_request_timeout,
        dice_critical_threshold=dice_critical_threshold,
        dice_fumble_threshold=dice_fumble_threshold,
    )
