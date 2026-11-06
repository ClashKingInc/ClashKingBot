# Discord interaction Worker

`POST /interactions` verifies Discord's Ed25519 signature before routing a
request. `src/runtime.ts` supplies API and Discord services through an Effect
Layer. Each command module contains its definition and handler; the authoritative
registered command list is [`src/commands/registry.ts`](src/commands/registry.ts).

## Ownership and compatibility

The Worker serves member commands, reports, and persistent controls. Server setup
and automation configuration live in the Dashboard. The ClashKing API owns
application persistence and server authorization. Tracking owns gateway ingestion
and background delivery. The Worker never connects directly to the database.

Persistent controls must survive Worker isolate replacement and releases:

- Legacy base `link` and `who` controls resolve the imported SQL row by message
  ID. Attachment staging and the Discord component edit must succeed before the
  API finalizes the row's location. Failed conversion remains retryable.
- Legacy Legend-history and quick-action controls route through current handlers.
  Cached retired setup commands direct the user to `/setup` without retaining
  a hidden configuration write path.
- Ticket interactions forward the original signed request to the API. The API
  owns panel identity, staff authorization, transcripts, and ticket replay state.
- `/link` requires the invoking user's player API token, including for server
  administrators. Token handling and ownership transfer stay in the API.

Discord's native application-command permissions control command access. API
checks remain authoritative for each operation. Interaction visibility is fixed
at acknowledgement time; a private result after public deferral needs a separate
private follow-up. Keep that invariant in the registry's deferred response path.

Logs, reminders, and AutoBoards use best-effort background delivery. Ticket replay
state is a separate API capability; it is not a template for background delivery.

## Local development

Use Node 24 or newer. Copy `.dev.vars.example` to ignored `.dev.vars`, with the
Beta application's credentials and the local API service token. Registration
uses separate ignored `.env.dev` and `.env.prod` files based on
`.env.commands.example`.

```sh
npm ci
npm run check
npm run dev
```

`npm run dev` uses `wrangler.local.jsonc`, serves port 8788, and calls the local
API on port 8787. Check `/health` before using the dedicated Beta interaction
endpoint. The optional `LOCAL_TEST_USER_ID` gate limits signed requests to one
user and rejects non-loopback API targets when enabled. See
[local tunnels](docs/LOCAL_TUNNELS.md) for the managed endpoint arrangement.

`npm run check` validates locale key/placeholder parity, command metadata,
generated environment types, lint, TypeScript, and a Wrangler dry-run build.
Translations are authored content, not proof of native-speaker review. Retained
[service checks](../tooling/e2e/README.md) exercise the local implementation;
unit and isolated-helper suites are not retained.

## Release operations

The default Wrangler environment targets `clashking-discord-dev`; `--env prod`
targets `clashking-discord`. Configure `DISCORD_APPLICATION_ID`,
`DISCORD_PUBLIC_KEY`, `DISCORD_BOT_TOKEN`, and `CLASHKING_API_TOKEN` separately
for each environment. Never commit credentials or generated Wrangler state.

Apply the matching DevKit schema and release the API before dependent bot
behavior. Validate the candidate with `npm run check`, then use the explicitly
selected release operation:

```sh
npm run deploy:dev
npm run deploy:prod
npm run register:dev
npm run register:prod
```

Deployment and registration change external state. Registration replaces the
selected application's complete global command list, so inspect the registry
and target before running it. Discord supports one interaction endpoint per
application. Beta testing must use the Beta application and an authorized test
guild; a local process alone does not make Discord writes local.

A production rollout must also stop the retired gateway/runtime through its
hosting controller before enabling a competing consumer. Use Coolify for every
lifecycle operation on a Coolify-hosted service. Record actual deployed Worker
versions and verify API health and signed interaction behavior separately from
a successful build. A source merge or dry-run build is not deployment evidence.

## Manual role refresh

`/refresh` defers immediately, then asks the API to resolve authorized members and
create a request in `role_refresh_requests` with existing `role_refresh_jobs`.
The minute scheduler continues those jobs across Worker restarts. It publishes
progress to a normal bot-owned channel message; interaction tokens are never
stored and are not needed after the initial acknowledgement. Schema migration
066 must precede the API and Bot deployment.

Each member update combines the managed role delta and nickname into one PATCH,
merging against a fresh member read. The existing member lease serializes our
workers. Discord has no conditional member update, so another administrator's
edit between that final read and PATCH cannot be made atomic. Provider bucket
headers pace requests within a Worker isolate; authoritative 429 delays reschedule
durable jobs without exhausting their failure attempts. Other processes have
their own clients, so this is not a global distributed limiter.

Progress is best effort and retried by the scheduler, including after the last
member completes. Deleted/inaccessible messages surface a publication error;
member work is retained. Successful unchanged members count in totals but do not
fill result pages. Results remain for seven days.
