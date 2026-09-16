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

### Manual local integration test with the production application

`wrangler.local.jsonc` deliberately keeps `CLASHKING_API_BASE_URL=https://api.clashk.ing`. The chosen full integration path runs the Worker locally with the production Discord application and production API credentials: put the production application ID, public key, bot token, and `CLASHKING_API_TOKEN` in the ignored `.dev.vars`, then run `npm run dev`. The Worker stays at `http://127.0.0.1:8787`, but command actions make real production API mutations.

Discord supports one Interactions Endpoint URL per application, so this test temporarily routes all production application interactions to the local Worker. Perform the endpoint switch only with explicit execution approval and use this order:

1. Run `npm run check`, start `npm run dev`, and verify `curl http://127.0.0.1:8787/health` before changing Discord.
2. Expose `http://127.0.0.1:8787/interactions` through an HTTPS tunnel and record the production application's current Interactions Endpoint URL for restoration.
3. Confirm the archived Python bot and any other duplicate Discord gateway session are stopped. The Worker receives HTTP interactions and must not be paired with a second bot process during this test.
4. After explicit approval, switch the production application's Interactions Endpoint URL to the tunnel, run only the bounded test cases, and treat every command as a production write.
5. Restore the recorded production endpoint immediately after the test, or before any troubleshooting if the local Worker or tunnel fails. Verify the restored endpoint before stopping the tunnel and local Worker.

A separate development Discord application is the safer optional alternative because its endpoint switch does not redirect production traffic, but it is not required for the chosen procedure. Command registration and deployment are separate external changes: do not run `register:dev`, `register:prod`, `deploy:dev`, or `deploy:prod` as part of this test.

Wrangler's top level is development and `--env prod` is production. Secrets (`DISCORD_APPLICATION_ID`, `DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, and `CLASHKING_API_TOKEN`) must be configured separately for each environment. Never commit `.dev.vars`, `.env.dev`, `.env.prod`, Wrangler state, or generated build output.

## Runtime boundary

The Worker calls the ClashKing API for every link and base mutation. It does not read the application database directly. Discord REST is used only for interaction callbacks, new-base attachment downloads, and the one-time edit that converts an existing legacy message. The API owns new-base message components and legacy attachment ingestion into ClashKing storage. The archived Python tree is reference material and is outside the active Worker TypeScript, lint, test, and Wrangler inputs.
