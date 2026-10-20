"""Logging configuration."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from resona.config.constants import PROJECT_NAME

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str | None = None) -> None:
    """Configure console and rotating file logging.

    Args:
        level: Log level name. Falls back to ``LOG_LEVEL`` then ``INFO``.
    """
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        logs_dir / f"{PROJECT_NAME.lower()}.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, resolved, logging.INFO),
        handlers=[console_handler, file_handler],
        force=True,
    )
