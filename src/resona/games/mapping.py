"""Translation between Resona identifiers and ``genshin.py`` types.

Only the three implemented games are mapped. Honkai Impact 3rd is deliberately
absent even though the library supports it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from resona.config.constants import GAME_GENSHIN, GAME_HSR, GAME_ZZZ

if TYPE_CHECKING:
    from genshin import Game

_LANG_ALIASES = {
    "zh": "zh-cn",
    "de": "de-de",
    "en": "en-us",
    "es": "es-es",
    "fr": "fr-fr",
    "id": "id-id",
    "it": "it-it",
    "ja": "ja-jp",
    "ko": "ko-kr",
    "pt": "pt-pt",
    "ru": "ru-ru",
    "th": "th-th",
    "tr": "tr-tr",
    "vi": "vi-vn",
}

_LIBRARY_LANGS = frozenset(_LANG_ALIASES.values())

_LIBRARY_GAMES = {
    GAME_GENSHIN: "GENSHIN",
    GAME_HSR: "STARRAIL",
    GAME_ZZZ: "ZZZ",
}


def library_game(game: str) -> Game:
    """Return the ``genshin.Game`` member for a Resona game identifier."""
    import genshin

    try:
        member = _LIBRARY_GAMES[game]
    except KeyError as exc:
        raise ValueError(f"Unsupported game: {game!r}") from exc

    return getattr(genshin.Game, member)


def business_ids(game: str) -> set[str]:
    """Every ``game_biz`` value that identifies ``game``, across regions."""
    import genshin

    member = library_game(game)
    return {mapping[member] for mapping in genshin.GAME_BIZS.values()}


def region_from_business_id(game: str, game_biz: str) -> str:
    """Map a ``game_biz`` value to ``os`` or ``cn``."""
    import genshin

    member = library_game(game)
    if game_biz == genshin.GAME_BIZS[genshin.Region.CHINESE][member]:
        return "cn"
    return "os"


def library_lang(locale: str | None) -> str:
    """Map a locale such as ``en`` to a supported ``genshin.py`` language."""
    if not locale:
        return "en-us"

    normalized = locale.lower().replace("_", "-")
    if normalized in _LIBRARY_LANGS:
        return normalized

    return _LANG_ALIASES.get(normalized.split("-")[0], "en-us")
