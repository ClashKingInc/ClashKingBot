# Discord interaction Worker

This package is the active ClashKing Bot runtime. `POST /interactions` verifies Discord's Ed25519 signature before routing a request. `src/runtime.ts` supplies API and Discord services through an Effect `Layer`; command modules contain the Discord definition and handler together so registration cannot drift from execution.

## Implemented slice

- `/base base_link description photo` validates the Clash layout URL, uploads the image through the API, creates the persisted base message, installs durable download/history buttons, records unique downloaders, and returns the layout link privately.
- `/link player user? api_token? greet?` preserves the legacy option names, enforces Manage Server/full-whitelist permissions for linking another member, respects `require_api_token_when_linking`, and delegates ownership verification and persistence to the API.
- `/unlink player` removes the invoking user's link through the API.
- `ck:link:start`, `ck:link:submit`, and `ck:link:help` provide isolate-safe link button/modal/help routing. `ck:base:download:<id>` and `ck:base:who:<id>` provide isolate-safe base interactions.

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

The Worker calls the ClashKing API for every link and base mutation. It does not read the application database directly. Discord REST is used only for interaction callbacks, attachment downloads, and adding persistent components to the API-created base message. The archived Python tree is reference material and is outside the Worker TypeScript, lint, test, and Wrangler globs.
