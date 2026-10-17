from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from telegram.ext import filters


COMMAND_NAME_RE = re.compile(r"^[a-z0-9_]{1,32}$")
GAME_NAME_RE = re.compile(r"^[a-z0-9_]+$")

VALID_SCOPES = {
    "private",
    "groups",
    "group_admins",
    "bot_admins",
    "owner",
}

VALID_PERMISSIONS = {
    "everyone",
    "group_admin",
    "bot_admin",
    "owner",
}


@dataclass(frozen=True)
class HandlerSpec:
    kind: str
    callback: Callable[..., Any]
    names: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    pattern: str | None = None
    message_filters: filters.BaseFilter | None = None
    group: int = 0
    game: str | None = None
    permission: str = "everyone"
    command_id: str | None = None
    scopes: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    canonical: str
    aliases: tuple[str, ...]
    game: str | None
    description: str
    scopes: tuple[str, ...]
    permission: str


_HANDLER_SPECS: list[HandlerSpec] = []
_COMMANDS_BY_ID: dict[str, CommandSpec] = {}
_COMMAND_NAME_TO_ID: dict[str, str] = {}
_CALLBACK_PATTERNS: dict[tuple[str, int], str] = {}
_FINALIZED = False


def add_handler_spec(spec: HandlerSpec) -> None:
    if _FINALIZED:
        raise RuntimeError(
            "The Resona handler registry is already finalized. "
            "Decorators must run before application registration."
        )
    _HANDLER_SPECS.append(spec)


def get_handler_specs() -> tuple[HandlerSpec, ...]:
    return tuple(_HANDLER_SPECS)


def get_commands() -> dict[str, CommandSpec]:
    return dict(_COMMANDS_BY_ID)


def get_command_id(name: str) -> str | None:
    return _COMMAND_NAME_TO_ID.get(name.lower().lstrip("/"))


def get_command_by_id(command_id: str) -> CommandSpec | None:
    return _COMMANDS_BY_ID.get(command_id)


def _validate_command_name(name: str, location: str) -> None:
    if not isinstance(name, str) or not COMMAND_NAME_RE.fullmatch(name):
        raise ValueError(
            f"{location}: invalid Telegram command name {name!r}. "
            "Use 1–32 lowercase ASCII letters, digits, or underscores."
        )


def _make_command_id(game: str | None, canonical: str) -> str:
    # Deterministic across restarts. Aliases never receive their own ID.
    return f"{game}_{canonical}" if game else f"core_{canonical}"


def validate_registry() -> None:
    """Validate all registrations atomically, before adding PTB handlers."""
    global _FINALIZED

    if _FINALIZED:
        return

    commands: dict[str, CommandSpec] = {}
    names_to_ids: dict[str, str] = {}
    patterns: dict[tuple[str, int], str] = {}

    errors: list[str] = []

    for index, spec in enumerate(_HANDLER_SPECS):
        location = (
            f"{spec.callback.__module__}."
            f"{spec.callback.__qualname__}"
        )

        if spec.kind == "command":
            if not spec.names:
                errors.append(f"{location}: command has no canonical name.")
                continue

            canonical = spec.names[0]
            aliases = spec.aliases

            for name in (canonical, *aliases):
                try:
                    _validate_command_name(name, location)
                except ValueError as exc:
                    errors.append(str(exc))

            if canonical in aliases:
                errors.append(
                    f"{location}: canonical command {canonical!r} "
                    "is repeated in its own aliases."
                )

            if len(set(aliases)) != len(aliases):
                errors.append(
                    f"{location}: duplicate aliases declared for "
                    f"{canonical!r}: {aliases!r}."
                )

            if spec.game is not None and not GAME_NAME_RE.fullmatch(spec.game):
                errors.append(
                    f"{location}: invalid game ID {spec.game!r}. "
                    "Use lowercase letters, digits, and underscores."
                )

            expected_id = _make_command_id(spec.game, canonical)
            command_id = spec.command_id or expected_id

            if command_id != expected_id:
                errors.append(
                    f"{location}: command ID {command_id!r} does not "
                    f"match its stable generated ID {expected_id!r}."
                )

            if command_id in commands:
                previous = commands[command_id]
                errors.append(
                    f"{location}: duplicate command ID {command_id!r}; "
                    f"already used by /{previous.canonical}."
                )
                continue

            if not spec.description or not spec.description.strip():
                errors.append(
                    f"{location}: command /{canonical} needs a "
                    "non-empty description."
                )

            command = CommandSpec(
                command_id=command_id,
                canonical=canonical,
                aliases=aliases,
                game=spec.game,
                description=(spec.description or "").strip(),
                scopes=spec.scopes,
                permission=spec.permission,
            )

            commands[command_id] = command

            for name in (canonical, *aliases):
                previous_id = names_to_ids.get(name)

                if previous_id is not None:
                    previous = commands[previous_id]
                    errors.append(
                        f"{location}: command-name collision for "
                        f"/{name}. It is claimed by both "
                        f"/{previous.canonical} "
                        f"(ID: {previous_id}) and "
                        f"/{canonical} (ID: {command_id}). "
                        "Canonical names and aliases must be globally unique."
                    )
                else:
                    names_to_ids[name] = command_id

        elif spec.kind == "callback":
            if spec.pattern is None:
                errors.append(f"{location}: callback pattern is missing.")
            else:
                key = (spec.pattern, spec.group)
                if key in patterns:
                    errors.append(
                        f"{location}: duplicate callback pattern "
                        f"{spec.pattern!r} in handler group {spec.group}; "
                        f"already registered by {patterns[key]}."
                    )
                else:
                    patterns[key] = location

        elif spec.kind == "message":
            if spec.message_filters is None:
                errors.append(f"{location}: message filters are missing.")

        else:
            errors.append(
                f"{location}: unsupported handler kind {spec.kind!r}."
            )

        if spec.permission not in VALID_PERMISSIONS:
            errors.append(
                f"{location}: invalid permission {spec.permission!r}; "
                f"expected one of {sorted(VALID_PERMISSIONS)}."
            )

        unknown_scopes = set(spec.scopes) - VALID_SCOPES
        if unknown_scopes:
            errors.append(
                f"{location}: invalid menu scopes {sorted(unknown_scopes)}."
            )

    if errors:
        details = "\n".join(f"  {i}. {error}" for i, error in enumerate(errors, 1))
        raise RuntimeError(
            "Resona registry validation failed. The bot will not start.\n"
            f"{details}"
        )

    # Commit only after every validation passes.
    _COMMANDS_BY_ID.update(commands)
    _COMMAND_NAME_TO_ID.update(names_to_ids)
    _CALLBACK_PATTERNS.update(patterns)
    _FINALIZED = True


def reset_registry_for_tests() -> None:
    """Test helper only. Do not call during normal bot operation."""
    global _FINALIZED
    _HANDLER_SPECS.clear()
    _COMMANDS_BY_ID.clear()
    _COMMAND_NAME_TO_ID.clear()
    _CALLBACK_PATTERNS.clear()
    _FINALIZED = False