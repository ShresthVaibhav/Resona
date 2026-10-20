"""TTL cache behaviour."""

from __future__ import annotations

from resona.core.cache import TTLCache


def test_returns_default_for_missing_key() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl=60)
    assert cache.get("missing") is None
    assert cache.get("missing", 5) == 5


def test_store_and_retrieve() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl=60)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert "a" in cache
    assert len(cache) == 1


def test_entries_expire(monkeypatch) -> None:
    clock = {"now": 0.0}
    monkeypatch.setattr("resona.core.cache.time.monotonic", lambda: clock["now"])

    cache: TTLCache[str, int] = TTLCache(ttl=10)
    cache.set("a", 1)

    clock["now"] = 9.0
    assert cache.get("a") == 1

    clock["now"] = 11.0
    assert cache.get("a") is None
    assert len(cache) == 0


def test_invalidate_and_clear() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl=60)
    cache.set("a", 1)
    cache.set("b", 2)

    cache.invalidate("a")
    assert cache.get("a") is None
    assert cache.get("b") == 2

    cache.clear()
    assert len(cache) == 0


def test_disabled_cache_never_stores() -> None:
    cache: TTLCache[str, int] = TTLCache(ttl=60, enabled=False)
    cache.set("a", 1)
    assert cache.get("a") is None
    assert len(cache) == 0


def test_purge_expired(monkeypatch) -> None:
    clock = {"now": 0.0}
    monkeypatch.setattr("resona.core.cache.time.monotonic", lambda: clock["now"])

    cache: TTLCache[str, int] = TTLCache(ttl=10)
    cache.set("a", 1)
    cache.set("b", 2)

    clock["now"] = 11.0
    assert cache.purge_expired() == 2
    assert len(cache) == 0
