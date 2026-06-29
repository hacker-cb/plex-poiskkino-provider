"""TTLCache behaviour."""

from __future__ import annotations

import pytest

from poiskkino_provider.cache import TTLCache


def test_set_get() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=100, max_entries=10)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None
    assert len(cache) == 1


def test_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 1000.0}
    monkeypatch.setattr("poiskkino_provider.cache.time.monotonic", lambda: clock["now"])
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=10, max_entries=10)
    cache.set("a", 1)
    clock["now"] = 1005.0
    assert cache.get("a") == 1  # still fresh
    clock["now"] = 1011.0
    assert cache.get("a") is None  # expired
    assert len(cache) == 0


def test_lru_eviction() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=100, max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # touch a -> b becomes least-recently-used
    cache.set("c", 3)  # evicts b
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_clear() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl_seconds=100, max_entries=10)
    cache.set("a", 1)
    cache.clear()
    assert len(cache) == 0
