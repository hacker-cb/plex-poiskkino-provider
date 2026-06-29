"""A tiny in-memory TTL cache to keep PoiskKino requests within the daily quota."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Bounded cache with per-entry TTL and LRU eviction.

    Single-threaded asyncio use only (no locking needed under the GIL for the
    simple dict operations here).
    """

    def __init__(self, *, ttl_seconds: float, max_entries: int) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: OrderedDict[K, tuple[float, V]] = OrderedDict()

    def _now(self) -> float:
        return time.monotonic()

    def get(self, key: K) -> V | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < self._now():
            del self._store[key]
            return None
        self._store.move_to_end(key)  # mark as recently used
        return value

    def set(self, key: K, value: V) -> None:
        self._store[key] = (self._now() + self._ttl, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max:
            self._store.popitem(last=False)  # evict least recently used

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
