from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AIRuntimeConfig:
    stream_output: bool = False


def load_ai_runtime_config(config_dir: Path) -> AIRuntimeConfig:
    general_file = Path(config_dir) / "general.toml"
    if not general_file.exists():
        return AIRuntimeConfig()

    current_section = ""
    stream_output = False
    for raw_line in general_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            continue
        if current_section == "ai" and "=" in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            if key == "stream_output":
                stream_output = value.lower() == "true"
    return AIRuntimeConfig(stream_output=stream_output)
