from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trpg_server.json_store import read_json


@dataclass(frozen=True)
class AgentRequestContext:
    room_id: str | None = None
    room_dir: Path | None = None
    scenarios_dir: Path | None = None
    user_id: str | int | None = None
    agent_id: str = "kp"

    def room_info(self) -> dict[str, Any]:
        if not self.room_dir:
            return {}
        return read_json(self.room_dir / "info.json", default={})

    def room_messages(self) -> list[dict[str, Any]]:
        if not self.room_dir:
            return []
        return read_json(self.room_dir / "messages.json", default=[])
