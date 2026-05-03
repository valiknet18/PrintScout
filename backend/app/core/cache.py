"""In-memory async TTL cache.

Mirrors the subset of `redis.asyncio.Redis` we use (`get`, `set(..., ex=...)`)
so call sites don't need to know we're not on Redis. Lost on process restart;
not shared across machines. Adequate for a single-machine MVP. Swap to Redis
by changing only this file when persistence/sharing is needed.
"""

from __future__ import annotations

import time
from typing import Optional


class InMemoryCache:
    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> Optional[str]:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        # Default TTL = 30d when caller omits ex (matches Redis "no-ttl" semantics
        # closely enough for our usage; without a cap, a long-running process
        # would leak entries forever).
        expires_at = time.monotonic() + (ex if ex else 30 * 24 * 60 * 60)
        self._data[key] = (value, expires_at)


_cache: InMemoryCache | None = None


def get_redis() -> InMemoryCache:
    """Returns the shared in-memory cache. Named `get_redis` for backwards
    compatibility with existing callers — no behavior depends on Redis."""
    global _cache
    if _cache is None:
        _cache = InMemoryCache()
    return _cache
