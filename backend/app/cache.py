import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Small process-local cache; it is intentionally not persistent storage."""

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> Any:
        if ttl_seconds > 0:
            self._entries[key] = CacheEntry(value, time.monotonic() + ttl_seconds)
        return value


station_cache = TTLCache()
route_cache = TTLCache()
live_cache = TTLCache()
