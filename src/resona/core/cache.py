"""A small TTL cache with explicit invalidation."""

from __future__ import annotations

import time
from collections.abc import Hashable
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """A minimal time-to-live cache.

    Entries expire after ``ttl`` seconds. ``ttl <= 0`` disables expiry, which is
    useful for per-request or test scopes.
    """

    __slots__ = ("_enabled", "_store", "_ttl")

    def __init__(self, ttl: float = 300.0, *, enabled: bool = True) -> None:
        self._ttl = float(ttl)
        self._store: dict[K, tuple[float, V]] = {}
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def get(self, key: K, default: V | None = None) -> V | None:
        if not self._enabled:
            return default
        entry = self._store.get(key)
        if entry is None:
            return default
        expires_at, value = entry
        if self._ttl > 0 and expires_at <= time.monotonic():
            self._store.pop(key, None)
            return default
        return value

    def set(self, key: K, value: V, *, ttl: float | None = None) -> None:
        if not self._enabled:
            return
        effective = self._ttl if ttl is None else float(ttl)
        expires_at = time.monotonic() + effective if effective > 0 else float("inf")
        self._store[key] = (expires_at, value)

    def invalidate(self, key: K) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def purge_expired(self) -> int:
        """Remove expired entries and return how many were removed."""
        if self._ttl <= 0:
            return 0
        now = time.monotonic()
        expired = [
            key for key, (expires_at, _) in self._store.items() if expires_at <= now
        ]
        for key in expired:
            self._store.pop(key, None)
        return len(expired)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        return self.get(key) is not None  # type: ignore[arg-type]
