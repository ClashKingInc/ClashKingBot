# Discord interaction Worker

This package is the active ClashKing Bot runtime. `POST /interactions` verifies Discord's Ed25519 signature before routing a request. `src/runtime.ts` supplies API and Discord services through an Effect `Layer`; command modules contain the Discord definition and handler together so registration cannot drift from execution.

## Implemented slice

- `/base base_link description photo photo_2? photo_3? photo_4?` validates the canonical Clash layout URL, uploads one to four images through the API, and asks the API to persist and post the Dashboard-compatible base message.
- `base:link:<id>`, `base:upvote:<id>`, and `base:downvote:<id>` record unique downloaders or one switchable vote per user. The link action returns the normalized layout link privately.
- Raw legacy `link` and `who` buttons resolve their preimported SQL row by Discord message ID, stage the message attachments in ClashKing-owned storage, edit the Discord components, and only then finalize the row's server, channel, and description. Failed copies or edits leave the row unconverted and can be retried.
- `/link player user? api_token? greet?` preserves the legacy option names, enforces Manage Server/full-whitelist permissions for linking another member, respects `require_api_token_when_linking`, and delegates ownership verification and persistence to the API.
- `/unlink player` removes the invoking user's link through the API.
- `ck:link:start`, `ck:link:submit`, and `ck:link:help` provide isolate-safe link button/modal/help routing.

Only these three command definitions are registered. Other reviewed experiment modules remain unregistered until their own compatibility slice is implemented and tested.

## Local setup

Use Node 24. Copy `.dev.vars.example` to `.dev.vars` and replace placeholders locally; `.dev.vars` is ignored. Command registration uses a separate ignored `.env.dev` or `.env.prod` copied from `.env.commands.example`.

```sh
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

`npm run build` is a Wrangler dry run. `register:*` changes Discord configuration and `deploy:*` changes Cloudflare state, so neither is part of routine validation beyond the safe dry run.

Wrangler's top level is development and `--env prod` is production. Secrets (`DISCORD_APPLICATION_ID`, `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, and `CLASHKING_API_TOKEN`) must be configured separately for each environment. Never commit `.dev.vars`, `.env.dev`, `.env.prod`, Wrangler state, or generated build output.

## Runtime boundary

The Worker calls the ClashKing API for every link and base mutation. It does not read the application database directly. Discord REST is used only for interaction callbacks, new-base attachment downloads, and the one-time edit that converts an existing legacy message. The API owns new-base message components and legacy attachment ingestion into ClashKing storage. The archived Python tree is reference material and is outside the Worker TypeScript, lint, test, Wrangler, and Sonar analysis globs.
