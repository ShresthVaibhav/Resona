# Project information
PROJECT_NAME = "Resona"
PROJECT_VERSION = "0.1.0"

# Supported games
GAME_GENSHIN = "genshin"
GAME_HSR = "hsr"
GAME_ZZZ = "zzz"
GAME_AKEF = "akef"

SUPPORTED_GAMES = (
    GAME_GENSHIN,
    GAME_HSR,
    GAME_ZZZ,
    GAME_AKEF,
)

# Telegram
DEFAULT_LANGUAGE = "en"
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024

# Pagination
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

# Cache defaults
DEFAULT_CACHE_TTL = 300

# Database collection names
USERS_COLLECTION = "users"
GROUPS_COLLECTION = "groups"
GROUP_SETTINGS_COLLECTION = "group_settings"
BOT_STATS_COLLECTION = "bot_stats"
