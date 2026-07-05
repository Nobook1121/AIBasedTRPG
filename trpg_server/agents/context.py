from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trpg_server.json_store import read_json
from trpg_server.security import safe_join


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


def build_agent_context(room_id, rooms_dir, scenarios_dir, user_id=None, agent_id="kp") -> AgentRequestContext:
    room_dir = safe_join(rooms_dir, room_id) if room_id else None
    return AgentRequestContext(
        room_id=str(room_id) if room_id else None,
        room_dir=room_dir,
        scenarios_dir=scenarios_dir,
        user_id=user_id,
        agent_id=agent_id,
    )
