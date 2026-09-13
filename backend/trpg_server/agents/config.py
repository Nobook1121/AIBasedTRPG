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


def load_ai_runtime_config(config_dir: Path) -> AIRuntimeConfig:
    general_file = Path(config_dir) / "general.toml"
    if not general_file.exists():
        return AIRuntimeConfig()

    current_section = ""
    stream_output = False
    debug_mode = False
    show_ai_hints = True
    small_model_tasks = AIRuntimeConfig().small_model_tasks.copy()
    for raw_line in general_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            continue
        if current_section in {"ai", "ai.small_models"} and "=" in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            if current_section == "ai.small_models":
                if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                    value = value[1:-1]
                small_model_tasks[key] = value
            elif key == "stream_output":
                stream_output = value.lower() == "true"
            elif key == "debug_mode":
                debug_mode = value.lower() == "true"
            elif key in {"show_ai_hints", "show_kp_hints", "reply_hints"}:
                show_ai_hints = value.lower() == "true"
    return AIRuntimeConfig(
        stream_output=stream_output,
        debug_mode=debug_mode,
        show_ai_hints=show_ai_hints,
        small_model_tasks=small_model_tasks,
    )
