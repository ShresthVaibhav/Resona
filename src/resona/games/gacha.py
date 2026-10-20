"""Shared gacha history behaviour for every game module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from resona.core.errors import (
    CredentialsExpiredError,
    CredentialsMissingError,
    ExternalAPIError,
    UserError,
)
from resona.games.common import GachaPity, render_gacha
from resona.games.mapping import library_game

if TYPE_CHECKING:
    from resona.services.accounts import AccountService

logger = logging.getLogger("resona.games.gacha")

_HISTORY_METHODS = {
    "genshin": "wish_history",
    "hsr": "warp_history",
    "zzz": "signal_history",
    "genshin_mw": "mw_wish_history",
}


class GachaHistoryMixin:
    """Adds recent gacha history to a game service.

    Services inherit this after defining ``game``, ``_accounts`` and
    ``gacha_command``.
    """

    game: str
    _accounts: AccountService
    gacha_command: str = "wishes"
    history_page_size: int = 10
    max_history_page: int = 20

    async def wishes(
        self,
        telegram_id: int,
        *,
        authkey: str | None = None,
        page: int = 1,
    ) -> str:
        """Return a page of recent pulls across every banner."""
        return await self._history(
            telegram_id,
            authkey=authkey,
            page=page,
            history_game=self.game,
            command=self.gacha_command,
            include_pity=True,
        )

    async def _history(
        self,
        telegram_id: int,
        *,
        authkey: str | None,
        page: int,
        history_game: str,
        command: str,
        include_pity: bool,
    ) -> str:
        if not 1 <= page <= self.max_history_page:
            raise UserError(f"Page must be between 1 and {self.max_history_page}.")

        account = await self._accounts.primary_account(telegram_id, self.game)
        if account is None:
            raise CredentialsMissingError()

        client = await self._accounts.build_client(telegram_id, self.game, account.uid)
        library_name = "genshin" if history_game == "genshin_mw" else history_game
        await _prepare_authkey(
            client,
            library_name,
            account.uid,
            authkey,
            command=command,
        )

        entries, has_more = await _collect_history(
            client,
            history_game,
            page=page,
            page_size=self.history_page_size,
        )

        pity: GachaPity | None = None
        if include_pity and page == 1 and entries:
            try:
                pity = await _collect_pity(
                    client,
                    history_game,
                    entries[0].banner_type,
                )
            except (UserError, ExternalAPIError):
                logger.warning(
                    "Pity lookup failed for %s; showing history without it.",
                    history_game,
                    exc_info=True,
                )

        return render_gacha(
            account,
            history_game,
            entries,
            page=page,
            page_size=self.history_page_size,
            has_more=has_more,
            pity=pity,
        )


async def _prepare_authkey(
    client: Any,
    game: str,
    uid: str,
    authkey: str | None,
    *,
    command: str,
) -> None:
    """Store a supplied authkey, or ask HoYoLAB for a temporary one."""
    import genshin

    library = library_game(game)
    if authkey:
        try:
            client.set_authkey(authkey, game=library)
        except (TypeError, ValueError) as exc:
            raise UserError(
                "That authkey could not be read. Send the full history URL "
                f"after /{command}."
            ) from exc
        return

    try:
        await client.fetch_authkey(int(uid), game=library)
    except RuntimeError as exc:
        # ``fetch_authkey`` is overseas-only; CN accounts must supply a URL.
        raise UserError(
            _authkey_help(command, "This region needs a manual authkey.")
        ) from exc
    except genshin.TooManyRequests as exc:
        raise UserError(
            "HoYoLAB is rate limiting requests. Please wait a few minutes."
        ) from exc
    except genshin.InvalidCookies as exc:
        raise UserError(
            _authkey_help(
                command,
                "The linked cookies do not include the token needed for history.",
            )
        ) from exc
    except genshin.GenshinException as exc:
        raise UserError(
            _authkey_help(command, "HoYoLAB could not issue an authkey.")
        ) from exc


async def _collect_history(
    client: Any,
    history_game: str,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Any], bool]:
    """Read one page of pulls across every banner, newest first."""
    entries: list[Any] = []
    fetch_limit = page * page_size + 1

    for banner in _banner_types(history_game):
        entries.extend(await _read_history(client, history_game, banner, fetch_limit))

    entries.sort(key=lambda entry: entry.time, reverse=True)
    start = (page - 1) * page_size
    window = entries[start : start + page_size]
    has_more = len(entries) > start + page_size
    return window, has_more


async def _collect_pity(
    client: Any,
    history_game: str,
    banner_type: Any,
) -> GachaPity | None:
    """Estimate pity for the banner of the newest pull."""
    if banner_type is None:
        return None

    cap = _hard_pity_cap(history_game, banner_type)
    entries = await _read_history(client, history_game, banner_type, cap + 1)
    entries.sort(key=lambda entry: entry.time, reverse=True)

    five_index = next(
        (index for index, entry in enumerate(entries) if entry.rarity == 5),
        None,
    )
    four_index = next(
        (index for index, entry in enumerate(entries) if entry.rarity >= 4),
        None,
    )

    if five_index is None:
        five = min(len(entries), cap)
        five_at_least = len(entries) > cap
    else:
        five = five_index
        five_at_least = False

    if four_index is None:
        four = min(len(entries), 10)
        four_at_least = len(entries) > 10
    else:
        four = four_index
        four_at_least = False

    return GachaPity(
        banner=_banner_label(banner_type),
        five_star=five,
        four_star=four,
        five_star_cap=cap,
        five_star_at_least=five_at_least,
        four_star_at_least=four_at_least,
    )


async def _read_history(
    client: Any,
    history_game: str,
    banner_type: Any,
    limit: int,
) -> list[Any]:
    import genshin

    method = getattr(client, _HISTORY_METHODS[history_game])
    entries: list[Any] = []

    try:
        async for entry in method(banner_type=banner_type, limit=limit):
            entries.append(entry)
    except genshin.AuthkeyTimeout as exc:
        raise UserError(
            "That authkey has expired. Open the in-game history again and "
            "copy a fresh URL."
        ) from exc
    except genshin.InvalidAuthkey as exc:
        raise UserError(
            "That authkey is not valid. Copy the history URL again."
        ) from exc
    except genshin.TooManyRequests as exc:
        raise UserError(
            "HoYoLAB is rate limiting requests. Please wait a few minutes."
        ) from exc
    except genshin.InvalidCookies as exc:
        raise CredentialsExpiredError() from exc
    except genshin.GenshinException as exc:
        logger.warning("Gacha history failed for %s: %s", history_game, exc)
        raise ExternalAPIError("Gacha history failed.") from exc

    return entries


def _banner_types(history_game: str) -> tuple[Any, ...]:
    import genshin.models as models

    if history_game == "genshin_mw":
        return tuple(models.MWBannerType)

    return {
        "genshin": tuple(models.GenshinBannerType),
        "hsr": tuple(models.StarRailBannerType),
        "zzz": tuple(models.ZZZBannerType),
    }[history_game]


def _hard_pity_cap(history_game: str, banner_type: Any) -> int:
    name = getattr(banner_type, "name", "")
    if history_game == "genshin" and name == "WEAPON":
        return 80
    if history_game == "hsr" and name in {"WEAPON", "FATE_WEAPON"}:
        return 80
    if history_game == "zzz" and name == "WEAPON":
        return 80
    return 90


def _banner_label(banner_type: Any) -> str:
    name = getattr(banner_type, "name", None)
    return name.replace("_", " ").title() if name else str(banner_type)


def _authkey_help(command: str, reason: str) -> str:
    return (
        f"{reason}\n\n"
        "Open the in-game history once, copy the page URL and send it after the "
        f"command:\n/{command} <history URL>\n\n"
        "You can also link again with the full Cookie request header so Resona "
        "can request an authkey automatically."
    )


__all__ = ["GachaHistoryMixin"]
