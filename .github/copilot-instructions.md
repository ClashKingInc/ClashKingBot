# ClashKing Bot — Copilot Instructions

A Clash of Clans Discord bot **in active migration from Python to Go**. The Python side (disnake + coc.py) is the current production bot; Go is being built alongside it.

## Ecosystem

ClashKingBot is one service in a larger platform:

| Repo | Role |
|---|---|
| **ClashKingBot** (this repo) | Discord bot — consumes ClashKingAPI `/v1` and `/v2` endpoints using the internal bot token |
| **ClashKingAPI** | REST API — serves data to the bot, dashboard, and mobile app (Python/FastAPI + Go/Fiber in migration) |
| **ClashKingTracking** | Python polling service — hits the official CoC API and writes raw data into MongoDB; the API only reads what tracking writes |
| **ClashKingDashboard** | Next.js web dashboard — consumes `/v2` endpoints |
| **ClashKingProxy** | Proxy in front of the official CoC API at `https://proxy.clashk.ing/v1` — coc.py requests route through this |

The bot calls `https://api.clashk.ing/` for data (stats, player info, clan info, etc.). The CoC API itself is accessed indirectly via the proxy.

## Architecture

This is a **dual-language project in active migration from Python (disnake) to Go (disgo)**. Both coexist in the same repository.

| Layer | Go (in progress) | Python (production) |
|---|---|---|
| Entry point | `main.go` | `main.py` |
| Discord library | [disgo](https://github.com/disgoorg/disgo) | disnake |
| Commands | `commands/` (Go files) | `commands/<feature>/commands.py` |
| Background tasks | `background/` (Go files) | `background/` (Python cogs) |
| Utilities | `utility/` (Go files) | `utility/` (Python modules) |
| API client | `api/` | HTTP via coc.py / requests |

## Build & Format

```bash
# --- Go ---
# Build
go build ./...

# Vet (lint)
go vet ./...

# Tests
go test ./...

# --- Python ---
# Format (line-length 150)
blue . && isort .

# Run the bot (requires .env with BOT_TOKEN)
python main.py
```

There is no automated test suite for Python. Confirm Python changes manually by running the bot.

## Go Conventions

### Command handler pattern

```go
// Commands are registered via handler.New() + r.SlashCommand("/name", handler)
r.SlashCommand("/clan", clanCommands.Handle)
r.Component("/button/{data}", clanCommands.Components)
```

### API client

The `api` package wraps calls to `https://api.clashk.ing/`. Add new endpoints there:

```go
func (c *apiClient) GetSomething(tag string) SomeModel {
    resp, _ := http.Get(fullUrl + "/some/path/" + tag)
    // ...
}
```

### Background tracking

Background services live in `background/`. The `ClanTracking` struct in `clan_tracking.go` is the reference implementation — it manages concurrency with goroutines + semaphore, bulk-writes to MongoDB, and has API health monitoring built in.

### Emoji access

Use `utility.Emojis.<Category>.<Name>.Mention()` — populated at startup by `utility.LoadEmojiConfig(client)`.

### Logging

Use `log/slog` (standard library). Do not use `fmt.Println` for operational logging.

## Python Architecture

### Startup flow
`main.py` → fetches remote config via API using `BOT_TOKEN` → instantiates `CustomClient` → loads extensions → starts bot.

All runtime config is fetched from `https://api.clashk.ing/bot/config` at startup (not from `.env`). Only `BOT_TOKEN` and optionally `CLUSTER_ID` are read from environment.

### `CustomClient` (`classes/bot.py`)
The central bot class extending `commands.AutoShardedBot`. It holds:
- Two `motor` async MongoDB clients:
  - **`db_client`** → `usafam` database (guild/server config, roles, bans, reminders, rosters, tickets, etc.)
  - **`looper_db`** → `new_looper`, `stats`, `cache`, `looper`, `clashking` databases (game tracking data)
- **`coc_client`** — coc.py client for the Clash of Clans API
- **`redis`** — async Redis client
- **`ck_client`** — `FamilyClient` instance (initialized after shard connect), used for all server/clan DB operations
- **`emoji`** — `Emojis` helper loaded dynamically from Discord application emojis
- **`i18n`** — `FluentStore` loaded from `locales/`

### Extension loading
- Extensions in `commands/` are auto-discovered by `load_cogs()` in `utility/startup.py` — it loads any file named `commands.py` or `buttons.py` inside `commands/<feature>/`.
- Additional fixed extensions are loaded from `discord/`, `background/`, and `exceptions/`.
- Some background extensions are **disabled in beta mode** (`config.is_beta`).

### Command structure
Each feature under `commands/<feature>/` follows this pattern:
- `commands.py` — the `commands.Cog` subclass with slash command definitions; always calls `await ctx.response.defer()` at the parent group level
- `utils.py` — business logic (embed builders, data fetching) called from the cog

Reusable command parameters live in `discord/options.py` (pre-built `commands.Param` instances with converters and autocomplete). Autocomplete handlers are in `discord/autocomplete.py`. Converters are in `discord/converters.py`.

### Event pipeline
Real-time Clash of Clans game events arrive via a WebSocket (`background/logs/events.py`). Events are dispatched using `pymitter` event emitters (`player_ee`, `clan_ee`, `war_ee`, etc.) and consumed by the `background/logs/` cogs.

### Localization
Commands use `disnake-ext-fluent`. Locale files are in `locales/<locale-code>/` as `.ftl` files. String keys are referenced with `disnake.Localized(key='...')`.

### Deployment
Releases are built as Docker images pushed to GHCR and deployed via Coolify webhook on GitHub Release publish. The bot supports horizontal sharding across clusters — shard assignment is computed from `config.cluster_id` and `config.total_clusters`.

## Python Key Conventions

- **Formatting**: `blue` formatter + `isort` with `profile = "black"` and `line_length = 150`. Always run both before committing.
- **Bot instance access**: All cogs receive `bot: CustomClient` in `__init__` and store it as `self.bot`. Never use globals.
- **DB access pattern**: Prefer `self.bot.ck_client` methods for server/clan reads (it wraps MongoDB with higher-level helpers). Use raw collection attributes on `self.bot` (e.g. `self.bot.clan_db`) for direct queries.
- **Slash commands**: All top-level group commands do `await ctx.response.defer()` immediately, then sub-commands call `ctx.edit_original_response(...)` to send the result.
- **Emoji access**: Use `self.bot.emoji.<name>` (instance of `Emojis`). Emoji definitions are fetched from Discord at shard connect, not hardcoded.
- **Logging**: Use `loguru` (`from loguru import logger`). Do not use `print` for operational logging.
- **Environment flags**: Check `bot._config.is_beta`, `is_main`, `is_custom` to gate features. Beta skips most background tasks and the WebSocket event pipeline.
- **New commands**: Add a folder under `commands/<feature>/` with `commands.py` (cog) and `utils.py`. The cog will be auto-discovered on next startup.

## Core Principles

- **Simplicity first** — make every change as simple as possible; impact minimal code.
- **No temporary fixes** — find root causes; senior developer standards.
- **Minimal impact** — only touch what's necessary.
- Security issues must be resolved **before any merge**.
