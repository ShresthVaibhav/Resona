"""Central argument validation."""

from __future__ import annotations

from types import SimpleNamespace

from resona.wrappers.registration import _validate_arguments
from resona.wrappers.registry import HandlerSpec


def _spec(**kwargs) -> HandlerSpec:
    kwargs.setdefault("names", ("demo",))
    return HandlerSpec(kind="command", callback=lambda: None, **kwargs)


def test_no_arguments_required() -> None:
    assert _validate_arguments(_spec(), SimpleNamespace(args=[])) is None


def test_required_argument_satisfied() -> None:
    spec = _spec(min_args=1)
    assert _validate_arguments(spec, SimpleNamespace(args=["123"])) is None


def test_missing_required_argument_reports_usage() -> None:
    spec = _spec(min_args=1, usage="/demo <uid>")
    message = _validate_arguments(spec, SimpleNamespace(args=[]))
    assert message is not None
    assert "Usage: /demo <uid>" in message


def test_too_many_arguments_rejected() -> None:
    spec = _spec(max_args=1)
    message = _validate_arguments(spec, SimpleNamespace(args=["a", "b"]))
    assert message is not None
    assert "Invalid arguments" in message


def test_unlimited_arguments_allowed() -> None:
    spec = _spec(max_args=None)
    assert _validate_arguments(spec, SimpleNamespace(args=["a", "b", "c"])) is None


def test_falls_back_to_command_name_in_usage_hint() -> None:
    spec = _spec(names=("demo",), min_args=1)
    message = _validate_arguments(spec, SimpleNamespace(args=[]))
    assert message is not None
    assert "/demo" in message
