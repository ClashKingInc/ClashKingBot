# Discord interaction Worker

This package is the active ClashKing Bot runtime. `POST /interactions` verifies Discord's Ed25519 signature before routing a request. `src/runtime.ts` supplies API and Discord services through an Effect `Layer`; command modules contain the Discord definition and handler together so registration cannot drift from execution.

## Implemented slice

- `/base` opens a modal with a layout link, multiline description (1–1,000 characters), and 1–4 screenshots. Submitted Label/File Upload components resolve attachment IDs through Discord's `resolved.attachments`. The Worker validates all metadata, uploads sequentially, and asks the API to persist and post standalone text and images. Newlines and literal `&&` are preserved.
- `base:link:<id>`, `base:upvote:<id>`, and `base:downvote:<id>` record unique downloaders or one switchable vote per user. The link action returns the normalized layout link privately.
- Raw legacy `link` and `who` buttons resolve their preimported SQL row by Discord message ID, stage the message attachments in ClashKing-owned storage, edit the Discord components, and only then finalize the row's server, channel, and description. Failed copies or edits leave the row unconverted and can be retried.
- `/link` opens a self-only modal with required player tag and API token, settings/help links, and no slash options. Missing tokens are rejected even for administrators. The API verifies and immediately transfers other-owned accounts; there is no confirmation step. Already-verified self links return an explicit response; unverified self links are verified. The bot never reads the old token-policy or full-whitelist settings. Dashboard behavior is unchanged.
- `/unlink player` removes the invoking user's link through the API.
- `ck:link:start`, `ck:link:submit`, and `ck:link:help` provide isolate-safe link button/modal/help routing.

- `/roster` opens a private roster picker, with creation and signup modals and standalone snapshot posts. See [roster implementation and review log](docs/ROSTERS_IMPLEMENTATION.md) for exact scope and unfinished API/Dashboard work.
- `/ticket panel-post` publishes a saved Dashboard panel in the invoking channel (Manage Server or Administrator required). Panel buttons and single-choice menus bind to saved ticket actions. Applications use the roster-style modal: the linked-account selector is the first field when enabled, followed by text, yes/no or dropdown questions. Opening messages support a full Classic/components-v1 or Components-v2 payload; the API snapshots it before submission and sends it separately from the application summary and staff controls. Optional private staff threads retain the application copy. `/ticket status` opens, sleeps or closes a ticket; `/ticket add` adds a member. Application controls support closing, clan assignment, shared message templates and account viewing. The Bot forwards the original signed interaction; the API authorizes staff actions and journals Discord effects for replay-safe delivery through its ticket Durable Object.
- Ticket deletion/transcript export and reply notifications are not enabled. Those unfinished controls are not advertised. Applicants without linked accounts use the existing `/link` flow before retrying the panel button.

The registry exposes eight command definitions. Updating the local registry does not change Discord until registration is explicitly run. The bulk registration script replaces the application's global command list; review that scope before running it. Other reviewed experiment modules remain unregistered until their own compatibility slice is implemented and tested.

## Localization and permissions

All 32 Discord locales are covered by 31 catalogs (British English uses en-US) for the current command names/descriptions, modal text, validation, private replies, and base controls. There is no separate UK English catalog. The Spanish catalogs intentionally share equivalent wording. Translations are an initial authored set, not a claim of native-speaker review. Add translated keys alongside future command work; `check:locales` enforces key/placeholder parity and tests cover supported locales and component limits.

Private replies use the actor's Discord locale, falling back to the guild locale and then English. Shared base buttons use `guild_locale`; the bot does not read or change Dashboard settings. New-base publication is API-owned and initially uses its English label; the bot applies a component-only localization edit. A failed label edit leaves the successfully published base intact rather than reposting it. The illustrated token-help image is the existing English guide, linked from translated modal text.

Command access is controlled through Discord's native application-command permissions (Server Settings → Integrations). No custom bot whitelist or privileged verification bypass remains. Existing Discord permission overrides are not migrated or edited automatically. The Dashboard's independent grants remain unchanged.

Modal launches respond immediately; submissions defer privately before API/media work. No token is persisted or echoed in errors. Image downloads are restricted to Discord CDN hosts, reject redirects, and enforce a 25 MiB streaming ceiling; image content validation remains API-owned. There are no automatic mutation retries. The existing API does not provide durable interaction receipts/idempotency for base creation, so duplicate interaction delivery and uncertain publication still require API-side work; users are told to check the channel before retrying an uncertain post.

## Local setup

Use Node 24. Copy `.dev.vars.example` to `.dev.vars` and replace placeholders locally; `.dev.vars` is ignored. Command registration uses a separate ignored `.env.dev` or `.env.prod` copied from `.env.commands.example`.

```sh
npm ci
npm run lint
npm run typecheck
npm run check:commands
npm run build
```

`npm run build` is a Wrangler dry run. `register:*` changes Discord configuration and `deploy:*` changes Cloudflare state, so neither is part of routine validation beyond the safe dry run.

### Local API integration testing

`npm run dev` uses `wrangler.local.jsonc`, listens on `http://127.0.0.1:8788`, and calls the local API at `http://127.0.0.1:8787`. The API token in ignored `.dev.vars` must match the local API, not production. Keep the existing Discord application credentials for Discord transport. API, Timescale and Dashboard setup status is recorded in the roster implementation log.

`LOCAL_TEST_USER_ID` is empty, so local beta testing is open to other Discord users under normal command permissions. It can optionally restrict signed interactions to one user; that opt-in mode also rejects non-loopback API URLs. Local development uses the beta Discord application and loopback API.

Discord supports one Interactions Endpoint URL per application. Local verification uses the dedicated Beta application, never a production endpoint switch. Use this order:

1. Run `npm run check`, start `npm run dev`, and verify `curl http://127.0.0.1:8788/health` before changing Discord.
2. Use the existing managed Beta tunnel for `http://127.0.0.1:8788/interactions`. Any Beta endpoint change requires explicit approval.
3. Confirm the archived Python bot and any other duplicate Discord gateway session are stopped. The Worker receives HTTP interactions and must not be paired with a second bot process during this test.
4. Run bounded cases only after confirming the Beta application and local API target. Discord messages are real external writes and need an authorized destination. Confirm any other upstream API/OAuth dependencies separately.
5. If a temporary Beta endpoint change was approved, restore that Beta endpoint when finished. Do not modify production.

Command registration and deployment are separate external changes: do not run `register:dev`, `register:prod`, `deploy:dev`, or `deploy:prod` without explicit approval. Retained actual-service checks are documented in `../tooling/e2e/README.md`; unit and isolated-helper suites are not retained.

Wrangler's top level is development and `--env prod` is production. Secrets (`DISCORD_APPLICATION_ID`, `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, and `CLASHKING_API_TOKEN`) must be configured separately for each environment. Never commit `.dev.vars`, `.env.dev`, `.env.prod`, Wrangler state, or generated build output.

## Runtime boundary

The Worker calls the ClashKing API for every link and base mutation. It does not read the application database directly. Discord REST is used for interaction callbacks, bounded attachment downloads, localized base controls, and legacy message conversion. The API owns publication, ownership transfers, and image storage. Bot-only token enforcement is not a global API-policy change: other API clients retain their existing contracts. The archived Python tree is reference material and is outside the active Worker TypeScript, lint, test, and Wrangler inputs.

## Role refresh

`/refresh` reconciles configured roles across all visible linked accounts and applies the server nickname rule. It defaults to the invoking member; staff can target a member or Discord role. `test` previews changes and `advanced_mode` selects categories without changing other configured categories. `/main-account` chooses a visible linked account for this server's nickname; every visible account still contributes roles.

Roles & Nicknames in the Dashboard combines family, leadership, player roles and nickname configuration. Role rules always reconcile eligibility; the obsolete stored add/remove mode and family-settings access grants are updated by the consolidated schema extension 022.

Automatic refresh runs whenever tracked account data is ingested, with clan events also queued through the durable API queue. There are no configurable triggers. Clan-leave grace is an integer 5–60 minutes, default 5, measured from the observed leave event. Other events preserve that grace; joining a family clan ends the grace and queues an immediate evaluation. Current account data is fetched when work runs. Polling, the one-minute production consumer and backlog can add latency. Missing player data stops changes rather than treating an account as ineligible.

Per-member leases serialize automatic and manual changes. The consumer handles two members concurrently and changes individual Discord roles, preserving unrelated roles. Completed request records expire after seven days with bounded cleanup. Apply the consolidated schema extension 022 before running updated API, Tracking, Bot and Dashboard; production deployment and Discord command registration are separate steps. Local testing does not enable the production cron.

Refresh command metadata has English fallback entries in every locale; the new refresh replies are currently English.
