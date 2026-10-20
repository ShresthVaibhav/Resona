"""Per-key rate limiting."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Hashable
from typing import TypeVar

K = TypeVar("K", bound=Hashable)


class RateLimiter:
    """A sliding-window rate limiter.

    Tracks timestamps per key and allows at most ``per_minute`` events in the
    trailing 60 seconds. ``per_minute <= 0`` disables limiting.
    """

    __slots__ = ("_clock", "_events", "_limit", "_window")

    def __init__(
        self, per_minute: int, *, window: float = 60.0, clock=time.monotonic
    ) -> None:
        self._limit = int(per_minute)
        self._window = float(window)
        self._events: dict[K, deque[float]] = {}
        self._clock = clock

    @property
    def limit(self) -> int:
        return self._limit

    def allow(self, key: K) -> bool:
        """Record an event for ``key`` and report whether it is allowed."""
        if self._limit <= 0:
            return True

        now = self._clock()
        events = self._events.setdefault(key, deque())
        self._evict(events, now)

        if len(events) >= self._limit:
            return False

        events.append(now)
        return True

    def retry_after(self, key: K) -> float:
        """Seconds until the next event would be allowed (0 when not limited)."""
        if self._limit <= 0:
            return 0.0

        now = self._clock()
        events = self._events.get(key)
        if not events:
            return 0.0

        self._evict(events, now)
        if len(events) < self._limit:
            return 0.0

        oldest = events[0]
        return max(0.0, self._window - (now - oldest))

    def reset(self, key: K | None = None) -> None:
        if key is None:
            self._events.clear()
        else:
            self._events.pop(key, None)

    def _evict(self, events: deque[float], now: float) -> None:
        cutoff = now - self._window
        while events and events[0] <= cutoff:
            events.popleft()
