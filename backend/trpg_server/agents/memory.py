import time
from typing import Any
from uuid import uuid4

from trpg_server.json_store import read_json, write_json_atomic

MAX_MEMORY_ITEMS = 200
MAX_MEMORY_CONTENT_LENGTH = 1000


def _memory_file(context: Any):
    if not context.room_dir:
        raise ValueError("room context is required for memory")
    return context.room_dir / "agent_memory.json"


def remember_room_fact(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    content = str(arguments.get("content") or "").strip()
    if not content:
        return {"error": "content is required"}
    item = {
        "id": uuid4().hex,
        "agent_id": getattr(context, "agent_id", "kp"),
        "kind": str(arguments.get("kind") or "fact")[:80],
        "content": content[:MAX_MEMORY_CONTENT_LENGTH],
        "importance": max(1, min(5, int(arguments.get("importance") or 1))),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = _memory_file(context)
    memory = read_json(path, default=[])
    memory.insert(0, item)
    write_json_atomic(path, memory[:MAX_MEMORY_ITEMS])
    return {"stored": True, "item": item}


def read_room_memory(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    path = _memory_file(context)
    query = str(arguments.get("query") or "").strip()
    limit = max(1, min(50, int(arguments.get("limit") or 10)))
    memory = read_json(path, default=[])
    if query:
        memory = [
            item
            for item in memory
            if query in str(item.get("content", "")) or query in str(item.get("kind", ""))
        ]
    memory.sort(
        key=lambda item: (int(item.get("importance") or 1), item.get("created_at", "")),
        reverse=True,
    )
    return {"items": memory[:limit]}
