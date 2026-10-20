# Resona

Resona is a Telegram bot that brings HoYoLAB utilities for HoYoverse games into
one place: real-time notes, characters, daily check-in, income diaries, gacha
history, endgame progress and event calendars.

It is built with [python-telegram-bot](https://python-telegram-bot.org/),
[genshin.py](https://github.com/genshinpy/genshin.py) and MongoDB.

## Supported games

| Game | Status | What works |
| --- | --- | --- |
| Genshin Impact | Implemented | Notes, characters, check-in, diary, wishes and Miliastra pulls, all three endgame modes, events |
| Honkai: Star Rail | Implemented | Notes, characters, check-in, diary, warps, Memory of Chaos, Pure Fiction, Apocalyptic Shadow, Anomaly Arbitration and Simulated Universe, events |
| Zenless Zone Zero | Implemented | Notes, agents, check-in, income diary, signals, Deadly Assault, Shiyu Defense, Annihilation Simulacrum and Lost Void, events |
| Wuthering Waves | Planned | No code in this repository yet |
| Arknights: Endfield | Planned | No code in this repository yet |
| Neverness to Everness | Planned | No code in this repository yet |

Honkai Impact 3rd is intentionally **not** supported.

Planned games are listed for transparency only. Commands for them do not exist
until their library surface has been verified and implemented.

## Features

- **One command set for three games.** Resolve the game from an argument, your
  default game, or the only account you have linked.
- **Cookie-based linking.** `/link` validates HoYoLAB cookies, detects the
  global or Chinese region, and stores them encrypted with Fernet.
- **Rich messages with a safety net.** Profile, accounts, help and the event
  digest render as rich cards on Bot API 10.1+ and fall back to plain text
  automatically.
- **Daily check-in job.** Claims the HoYoLAB reward for every linked account of
  users who left notifications enabled.
- **Opt-in event digest.** Once enabled with `/settings event_digest on`, Resona
  sends one daily message listing events that end within the next few days.
  Event calendars are cached briefly to avoid duplicate API calls.
- **Gacha history with a manual fallback.** `/wishes`, `/warp`, `/signals` and
  `/miliastra` show the newest pulls, page through older history and estimate
  pity on the latest banner. Resona requests a temporary authkey when HoYoLAB
  allows it; otherwise the in-game history URL can be supplied for that request
  only.
- **MongoDB persistence.** Users, settings, encrypted credentials and account
  metadata live in separate typed collections.
- **Central command registry.** Permissions, scopes, argument limits, rate limits
  and `/help` are generated from one declaration.

## Commands

The generic game commands (`/notes`, `/characters`, `/checkin`, `/diary`,
`/endgame` and `/events`) accept an optional game argument: `genshin`, `hsr` or
`zzz`. Without it, Resona uses your default game, or the only game you have
linked. Gacha commands are game-specific.

| Command | Aliases | Arguments | Scope | Description |
| --- | --- | --- | --- | --- |
| `/start` | | | Private, groups | Get started with Resona |
| `/about` | | | Private, groups | About Resona |
| `/ping` | | | Private, groups | Check that the bot is responding |
| `/help` | `/commands` | | Private, groups | List every available command |
| `/profile` | | | Private, groups | Show your Resona profile |
| `/settings` | | `[key] [value]` | Private | View or change preferences |
| `/link` | | `<game> <cookies>` or `<game> <uid> <cookies>` | Private | Link a HoYoLAB account |
| `/unlink` | | `[game]` | Private | Remove a linked account |
| `/accounts` | | | Private | List your linked accounts |
| `/notes` | `/stamina` | `[game]` | Private, groups | Show stamina and daily notes |
| `/characters` | | `[game]` | Private, groups | List your characters or agents |
| `/checkin` | | `[game]` | Private | Claim the daily HoYoLAB reward |
| `/diary` | | `[game]` | Private | Show this month's income |
| `/endgame` | | `[game]` | Private | Show endgame progress |
| `/events` | | `[game]` | Private, groups | Show active events |
| `/wishes` | | `[page] [history URL]` | Private | Show recent Genshin wishes |
| `/warp` | | `[page] [history URL]` | Private | Show recent Star Rail warps |
| `/signals` | | `[page] [history URL]` | Private | Show recent ZZZ signal searches |
| `/miliastra` | | `[page] [history URL]` | Private | Show recent Miliastra Wonderland pulls |

`/settings` accepts:

| Key | Values |
| --- | --- |
| `language` | Short locale such as `en`, `de` or `ja` |
| `timezone` | IANA name such as `Asia/Kolkata` or `UTC` |
| `game` | `genshin`, `hsr`, `zzz` or `none` |
| `notifications` | `on` or `off` |
| `event_digest` | `on` or `off` (default `off`) |

## Prerequisites

- Python 3.11 or newer
- MongoDB (local or hosted)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A HoYoLAB account with cookies you can copy from a browser

## Install

```bash
git clone <repository-url>
cd Resona
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install the project and its dependencies:

```bash
python -m pip install -e ".[dev]"
```

Or install only the runtime requirements:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Copy the example environment file and fill it in:

```bash
cp .env.example .env
```

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `BOT_TOKEN` | Yes | | Telegram bot token |
| `BOT_OWNER_ID` | Yes | | Telegram ID of the bot owner |
| `MONGO_URI` | Yes | | MongoDB connection string |
| `MONGO_DATABASE` | | `resona` | Database name |
| `COOKIE_ENCRYPTION_KEY` | For `/link` | | Fernet key used to encrypt cookies |
| `ENVIRONMENT` | | `development` | Environment label |
| `LOG_LEVEL` | | `INFO` | Logging level |
| `DEFAULT_LOCALE` | | `en` | Language used for HoYoLAB responses |
| `CONCURRENT_UPDATES` | | `32` | Maximum concurrent updates |
| `RICH_MESSAGES_ENABLED` | | `true` | Try rich messages before plain text |
| `CHECKIN_ENABLED` | | `true` | Enable the daily check-in job |
| `CHECKIN_HOUR_UTC` | | `16` | Hour of the check-in job (UTC) |
| `CHECKIN_MINUTE_UTC` | | `5` | Minute of the check-in job (UTC) |
| `EVENT_DIGEST_ENABLED` | | `true` | Enable the event digest job |
| `EVENT_DIGEST_HOUR_UTC` | | `9` | Hour of the event digest (UTC) |
| `EVENT_DIGEST_MINUTE_UTC` | | `0` | Minute of the event digest (UTC) |
| `EVENT_DIGEST_DAYS` | | `3` | Only include events ending within this many days |
| `CACHE_ENABLED` | | `true` | Cache event calendars |
| `CACHE_TTL` | | `300` | Event calendar cache lifetime in seconds |
| `RATE_LIMIT_PER_MINUTE` | | `20` | Per-user command limit |
| `MAINTENANCE_MODE` | | `false` | Reject commands with the maintenance message |
| `LOCAL_BOT_API` | | `false` | Use a local Bot API server |
| `BOT_API_BASE_URL` | | `http://127.0.0.1:8081/bot` | Local Bot API base URL |
| `BOT_API_FILE_URL` | | `http://127.0.0.1:8081/file/bot` | Local Bot API file URL |

See `.env.example` for the complete list, including admin IDs and maintenance text.

Generate the encryption key once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep `.env` private. It is already ignored by Git.

## Database setup

Create the collections and indexes:

```bash
python scripts/initialize_database.py
```

The script is idempotent, so it is safe to run on every deploy.

## Run

```bash
python run.py
```

or, after an editable install:

```bash
python -m resona
```

## Linking an account

1. Sign in at [hoyolab.com](https://www.hoyolab.com/).
2. Open your browser's developer tools and find a request to `hoyolab.com`.
3. Copy the full `Cookie` request header.
4. Send it to the bot:

```text
/link genshin ltuid_v2=...; ltoken_v2=...; ltmid_v2=...
```

If several accounts are bound to the same cookies, include the UID:

```text
/link hsr 800000001 ltuid_v2=...; ltoken_v2=...; ltmid_v2=...
```

Resona deletes the message containing the cookies when Telegram allows it, then
stores the cookies encrypted. Use `/unlink` to remove them.

## Gacha history

`/wishes`, `/warp` and `/signals` return the last 10 pulls across every banner,
newest first. Add a page number to read older pulls:

```text
/wishes 2
/warp 3
```

The first page also shows an **estimated pity** counter for the banner of the
newest pull. It fetches enough recent history for that banner to count pulls
since the last 5-star and 4-star. It is an estimate, not a guarantee tracker:
the 50/50 state and banner-specific rules are not modelled.

`/miliastra` reads Genshin Impact's Miliastra Wonderland history separately and
uses the same paging arguments.

Resona first asks HoYoLAB for a temporary authkey. That requires the
`cookie_token_v2` cookie, so if the account was linked with an older cookie
header, link again with the full current `Cookie` header. If HoYoLAB does not
issue an authkey (for example on the Chinese region), open the in-game history
once, copy the page URL and send it after the command:

```text
/wishes https://...authkey=...
/wishes 2 https://...authkey=...
```

The page number and URL can be supplied in either order. The authkey is used for
that request only and is never persisted.

## Rich messages

Rich messages were introduced in Bot API 10.1. python-telegram-bot 22.8 targets
Bot API 10.0, so Resona sends rich payloads through an isolated compatibility
layer in `src/resona/core/rich/` instead of monkey-patching the library.

- Payloads are validated against the documented limits before sending.
- If the API rejects a payload, or the bot runs on an older Bot API server, the
  same content is sent as plain text.
- Set `RICH_MESSAGES_ENABLED=false` to skip rich messages entirely.
- Incoming rich messages are ignored; Resona only sends them.

## Background jobs

The daily check-in job runs once per day at `CHECKIN_HOUR_UTC:CHECKIN_MINUTE_UTC`.
The default, 16:05 UTC, is shortly after the HoYoLAB daily reset at 00:00 UTC+8.
It only checks in accounts belonging to users whose `notifications` setting is
enabled, reports each account in one summary message, and keeps going when one
account fails.

The event digest runs once per day at `EVENT_DIGEST_HOUR_UTC:EVENT_DIGEST_MINUTE_UTC`
(default 09:00 UTC). It is **opt-in**: a user must enable both `notifications` and
`event_digest` with `/settings`. One message lists each game's events ending within
`EVENT_DIGEST_DAYS`; games without upcoming events are omitted, and one failed game
does not hide the others. Event calendars are cached for `CACHE_TTL` seconds, and
the digest is sent as a rich card when Bot API 10.1+ is available.

When `CACHE_ENABLED` is true, a maintenance job runs every hour and removes expired
cache entries. This keeps the process from retaining stale event calendars after
their TTL.

These jobs use PTB's `JobQueue`; make sure the `job-queue` extra is installed (it is
part of `requirements.txt` and the project dependencies).

## Tests and checks

```bash
pytest
ruff check .
ruff format --check .
python scripts/check_registry.py
```

Tests use in-memory repository doubles and mocked Telegram/library clients; no
real credentials or MongoDB server are required.

## Project layout

```text
src/resona/
├── application.py       # application construction and lifecycle
├── bootstrap.py         # entry point
├── config/              # settings, constants, logging
├── core/                # context, errors, cache, rate limiting, rich messages
├── database/            # Mongo client, collections, repositories
├── games/               # per-game services and renderers
├── handlers/            # Telegram command handlers
├── jobs/                # scheduled background work
├── services/            # account linking, users, game dispatch
└── wrappers/            # registry, decorators, permissions, error handling
```

## Adding a command

1. Add a handler in `src/resona/handlers/` using the `@command(...)` decorator.
2. Give it a unique canonical name, a description, a category and the scopes it
   supports.
3. Run `python scripts/check_registry.py` and the test suite.

The registry rejects duplicate names and aliases at startup.

## Adding a game

1. Verify the library methods and response fields against the installed
   `genshin.py` version or its documentation. Do not guess.
2. Add the identifier and label in `config/constants.py`.
3. Add the `genshin.Game` mapping in `games/mapping.py`.
4. Create a game package with a service and views, following `games/genshin/`.
5. Register the service in `services/games.py` and add tests.

Games without a verified surface stay in `PLANNED_GAMES` and get no code.

## Troubleshooting

- **`/link` says the cookies are invalid.** Copy the full `Cookie` header again;
  HoYoLAB cookies expire and are rotated.
- **A command says notes or diary are not public.** Enable the matching privacy
  setting in the game's HoYoLAB settings.
- **HoYoLAB is rate limiting.** Wait a few minutes. Resona limits command usage,
  but the upstream API has its own limits.
- **`/wishes` asks for a history URL.** The linked cookie header is missing
  `cookie_token_v2`, or the account is on the Chinese region. Link again with the
  full header, or paste the in-game history URL after the command.
- **The gacha authkey expired.** Open the in-game history again and copy a fresh
  URL. Authkeys are short-lived.
- **Rich messages look like plain text.** The bot is probably running on Bot API
  10.0 or an older local server. This is expected and safe.
- **No check-in summary arrived.** Check `CHECKIN_ENABLED`, the user's
  `notifications` setting, and whether the bot was blocked.
- **No event digest arrived.** The digest is opt-in: enable both `notifications`
  and `event_digest`, and check `EVENT_DIGEST_ENABLED`. It is only sent when an
  event ends within `EVENT_DIGEST_DAYS`.
- **`/link` says linking is not configured.** Set `COOKIE_ENCRYPTION_KEY` and
  restart the bot.

## Security

- HoYoLAB cookies are encrypted at rest with Fernet and are never logged.
- Gacha authkeys are held in memory for one request and are never persisted.
- Secrets come from the environment; `.env` is ignored by Git.
- The bot only supports cookie-based linking. It never asks for a password.
- Payments are out of scope for this version.

## Contributing

Keep changes focused, add tests with new behaviour, and run the checks above
before opening a pull request. Commit messages follow the conventional prefixes
used in the history (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).

## License

MIT. See [LICENSE](LICENSE).
