"""Static project constants."""

from __future__ import annotations

# Project information
PROJECT_NAME = "Resona"
PROJECT_VERSION = "0.1.0"

# Supported games (identifier used everywhere in code and the registry)
GAME_GENSHIN = "genshin"
GAME_HSR = "hsr"
GAME_ZZZ = "zzz"
GAME_WUTHERING_WAVES = "wuthering_waves"
GAME_ARKNIGHTS_ENDFIELD = "arknights_endfield"
GAME_NEVERNESS_TO_EVERNESS = "neverness_to_everness"

# Games backed by a verified library integration and therefore implemented.
IMPLEMENTED_GAMES = (GAME_GENSHIN, GAME_HSR, GAME_ZZZ)

# Games that are documented as planned only; no code module exists for them.
PLANNED_GAMES = (
    GAME_WUTHERING_WAVES,
    GAME_ARKNIGHTS_ENDFIELD,
    GAME_NEVERNESS_TO_EVERNESS,
)

SUPPORTED_GAMES = IMPLEMENTED_GAMES + PLANNED_GAMES

GAME_LABELS = {
    GAME_GENSHIN: "Genshin Impact",
    GAME_HSR: "Honkai: Star Rail",
    GAME_ZZZ: "Zenless Zone Zero",
    GAME_WUTHERING_WAVES: "Wuthering Waves",
    GAME_ARKNIGHTS_ENDFIELD: "Arknights: Endfield",
    GAME_NEVERNESS_TO_EVERNESS: "Neverness to Everness",
}

# Command categories
CATEGORY_GENERAL = "General"
CATEGORY_HELP = "Help"
CATEGORY_GAMES = "Games"
CATEGORY_PROFILE = "Profile"
CATEGORY_ACCOUNT = "Account"
CATEGORY_NOTIFICATIONS = "Notifications"
CATEGORY_ADMIN = "Admin"

# Telegram limits
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024

# Pagination
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

# Cache defaults
DEFAULT_CACHE_TTL = 300
