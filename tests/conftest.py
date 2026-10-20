"""Shared test fixtures and environment defaults."""

from __future__ import annotations

import os

# Provide a minimal, valid environment before any settings are loaded.
os.environ.setdefault("BOT_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("BOT_OWNER_ID", "1")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

import pytest

from resona.config.settings import reset_settings_cache
from resona.wrappers.registry import reset_registry_for_tests


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset the registry and cached settings around every test."""
    reset_registry_for_tests()
    reset_settings_cache()
    yield
    reset_registry_for_tests()
    reset_settings_cache()
