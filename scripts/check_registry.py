"""Validate the command registry without starting the bot.

Usage:
    python scripts/check_registry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from resona.handlers import load_handlers
from resona.wrappers.registry import get_commands, validate_registry


def main() -> None:
    try:
        load_handlers()
        validate_registry()
    except Exception as exc:
        print(f"Registry validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    commands = sorted(get_commands().values(), key=lambda spec: spec.canonical)
    print(f"Registry OK: {len(commands)} commands")
    for spec in commands:
        aliases = f" (aliases: {', '.join(spec.aliases)})" if spec.aliases else ""
        print(f"  /{spec.canonical}{aliases} - {spec.description}")


if __name__ == "__main__":
    main()
