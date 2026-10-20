"""Availability controller behaviour."""

from __future__ import annotations

from resona.core.availability import AvailabilityController


async def test_maintenance_blocks_commands_and_games() -> None:
    controller = AvailabilityController(maintenance=True)
    assert await controller.is_command_enabled(command_id="core_ping") is False
    assert await controller.is_game_enabled(game="genshin") is False


async def test_disabled_command_only_blocks_that_command() -> None:
    controller = AvailabilityController(disabled_commands={"core_ping"})
    assert await controller.is_command_enabled(command_id="core_ping") is False
    assert await controller.is_command_enabled(command_id="core_help") is True


async def test_disabled_game_blocks_its_commands() -> None:
    controller = AvailabilityController(disabled_games={"zzz"})
    assert (
        await controller.is_command_enabled(command_id="zzz_notes", game="zzz") is False
    )
    assert await controller.is_game_enabled(game="zzz") is False
    assert await controller.is_game_enabled(game="genshin") is True


async def test_per_chat_override_only_affects_that_chat() -> None:
    controller = AvailabilityController()
    controller.set_chat_command_disabled(-100, "core_ping", disabled=True)

    assert (
        await controller.is_command_enabled(command_id="core_ping", chat_id=-100)
        is False
    )
    assert (
        await controller.is_command_enabled(command_id="core_ping", chat_id=-200)
        is True
    )

    controller.set_chat_command_disabled(-100, "core_ping", disabled=False)
    assert (
        await controller.is_command_enabled(command_id="core_ping", chat_id=-100)
        is True
    )


def test_toggle_helpers_update_state() -> None:
    controller = AvailabilityController()

    controller.disable_game("hsr")
    assert "hsr" in controller.disabled_games
    controller.enable_game("hsr")
    assert "hsr" not in controller.disabled_games

    controller.set_maintenance(True, message="Down for upgrades")
    assert controller.maintenance is True
    assert controller.unavailable_message() == "Down for upgrades"


def test_feature_flags_default_to_disabled() -> None:
    controller = AvailabilityController()
    assert controller.is_feature_enabled("new_ui") is False
    assert controller.is_feature_enabled("new_ui", default=True) is True

    controller.set_feature_flag("new_ui", True)
    assert controller.is_feature_enabled("new_ui") is True


def test_snapshot_is_serialisable() -> None:
    controller = AvailabilityController(disabled_games={"zzz"})
    controller.set_feature_flag("beta", True)

    snapshot = controller.snapshot()
    assert snapshot["disabled_games"] == ["zzz"]
    assert snapshot["feature_flags"] == {"beta": True}
