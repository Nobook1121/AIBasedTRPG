from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    value: Any
    expires_at: float
    hits: int = 0


class _TTLCache:
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = max(1, int(default_ttl))
        self._entries: dict[str, _Entry] = {}

    def _get(self, key: str) -> _Entry | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.expires_at <= time.time():
            self._entries.pop(key, None)
            return None
        entry.hits += 1
        return entry

    def get(self, key: str) -> Any:
        entry = self._get(str(key))
        return entry.value if entry else None

    def set(self, key: str, value: Any, ttl: int | None = None) -> Any:
        self._entries[str(key)] = _Entry(value=value, expires_at=time.time() + max(1, int(ttl or self.default_ttl)))
        return value

    def stats(self, key: str) -> dict[str, Any]:
        entry = self._entries.get(str(key))
        return {"hits": entry.hits if entry else 0, "present": bool(self._get(str(key)))}


class ProviderPrefixCache(_TTLCache):
    """Tracks stable provider prefixes; provider remains the source of truth for billing hits."""

    def lookup(self, cache_key: str, ttl: int | None = None) -> bool:
        if self._get(cache_key):
            return True
        self.set(cache_key, True, ttl=ttl)
        return False


class ExactResponseCache(_TTLCache):
    pass


class SemanticCache(_TTLCache):
    @staticmethod
    def _key(intent: str, state: dict[str, Any] | None) -> str:
        fingerprint = hashlib.sha256(
            json.dumps(state or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        return f"{str(intent).strip().casefold()}:{fingerprint}"

    def get(self, intent: str, state: dict[str, Any] | None) -> Any:
        return super().get(self._key(intent, state))

    def set(self, intent: str, state: dict[str, Any] | None, value: Any, ttl: int | None = None) -> Any:
        return super().set(self._key(intent, state), value, ttl=ttl)
