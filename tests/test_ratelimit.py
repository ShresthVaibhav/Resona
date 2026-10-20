"""Sliding-window rate limiter."""

from __future__ import annotations

from resona.core.ratelimit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_up_to_the_limit_then_blocks() -> None:
    clock = FakeClock()
    limiter = RateLimiter(3, clock=clock)

    assert [limiter.allow("user") for _ in range(4)] == [True, True, True, False]


def test_limit_is_per_key() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, clock=clock)

    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_window_slides() -> None:
    clock = FakeClock()
    limiter = RateLimiter(2, clock=clock)

    assert limiter.allow("user") is True
    clock.advance(30)
    assert limiter.allow("user") is True
    assert limiter.allow("user") is False

    clock.advance(31)  # first event is now older than 60s
    assert limiter.allow("user") is True


def test_retry_after_reports_wait_time() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, clock=clock)

    limiter.allow("user")
    assert limiter.retry_after("user") == 60.0

    clock.advance(20)
    assert limiter.retry_after("user") == 40.0


def test_disabled_when_limit_is_zero() -> None:
    limiter = RateLimiter(0)
    assert limiter.allow("user") is True
    assert limiter.retry_after("user") == 0.0


def test_reset_clears_state() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, clock=clock)
    limiter.allow("user")

    limiter.reset("user")
    assert limiter.allow("user") is True
