# Local service checks

These scripts exercise real local workers and PostgreSQL. They are not unit tests.
They create identifiable synthetic records and delete only their own records in
`finally` blocks. Do not run concurrent copies of the same script.

Run from the bot repo with Node 24+, installed API dependencies, the migrated
local `clashking_dev` database, and the extracted assets:

```sh
node tooling/e2e/army-security.mjs
node tooling/e2e/command-parity.mjs
node tooling/e2e/command-parity.mjs --public-controls-only
node tooling/e2e/discord-delivery.mjs
node tooling/e2e/farming-autoboard-api.mjs
node tooling/e2e/army-presentation.mjs
```

The manual-reminder check requires an isolated, freshly migrated database. Run
the real schema harness from the schemas repository:

```sh
bash scripts/with-test-timescale.sh --profile retained-api -- node /absolute/path/to/clashking_bot/tooling/e2e/manual-reminders.mjs
```

It starts the full local API, the actual reminders domain, and the actual Discord
delivery domain. It verifies both authentication paths through PostgreSQL
notifications and Valkey, including the minimal notification payload without
an actor or version field, and no durable request or replay when the
listener is disconnected. Only external Clash/Discord HTTP responses use
loopback fixtures. Database clones disappear with the disposable container;
the script removes its unique Valkey stream and stops all owned processes.

The delivery check also requires Go and local Valkey. Set
`CLASHKING_E2E_VALKEY_PORT` and `CLASHKING_E2E_VALKEY_PASSWORD` in the invoking
environment when the local service requires them. The password is never logged.

Optional overrides:

- `CLASHKING_E2E_API_REPO`: API checkout; defaults to sibling `clashking_api`.
- `CLASHKING_E2E_ASSETS_REPO`: assets checkout; defaults to sibling `clashking_assets`.
- `CLASHKING_E2E_TRACKING_REPO`: Tracking checkout; defaults to sibling `clashking_tracking`.
- `CLASHKING_E2E_DATABASE_URL`: must remain `postgres://…@127.0.0.1:<port>/clashking_dev`.
- `CLASHKING_E2E_API_PORT`: army defaults to 8802; commands default to 8801.
  Army presentation uses 8803.
- `CLASHKING_E2E_BETA_EMOJIS=1`: command check additionally fetches the real Beta
  application emoji inventory with one authenticated, read-only Discord GET.
  Uses the API checkout's existing Beta credential loader (macOS Keychain or its
  explicit environment variables). The actual local lookup/group routes must
  emit existing `pekka`, `war_star`, `th16`, and `blue_1` IDs. The name probe is
  explicitly synthetic, not authentic player data or a Discord visual test.

The API scripts generate Ed25519 and service credentials for each run. The
delivery worker uses a fake Discord token. HTTP providers bind to loopback.
The command worker rejects outbound destinations other than its local API and
intercepts Discord requests. The army check disables the Clash provider. None
of these checks posts to a real Discord channel, changes application emojis,
publishes packages, or deploys a worker.

The army checks require one known local composition; pagination requires 30.
No second army library or synthetic army compositions are created. Runtime
build/storage files remain in OS temporary directories for failure diagnosis.

Coverage:

- Army signed actor binding, expiry, application identity, token enforcement,
  cross-user selection rejection, and scoped Clash proxy restrictions.
- Current Ranked profile/group selection, explicit historical season, retained
  history pagination, account pagination, and selection beyond 25 saved armies.
- Donation snapshot baseline, row limit, configured emoji names, edit-in-place,
  event coalescing, daily new message, empty reminder suppression, visible
  unlinked members, and two distinct confirmed mention recipients.
- Farming API configuration, cadence/window validation, persistent counting
  start, edit-in-place identity, and settings deletion. The delivery check also
  exercises all three resources, session duration, incomplete duration data,
  and the 30-second periodic schedule against real local PostgreSQL/Go code.
- Old-style army fields and named emoji quantities through real signed worker
  HTTP, no auto-save on preview, unknown-composition insertion only on Save,
  clicking-user ownership, repeated-save idempotency, bot-message/hash checks,
  absent-user rollback without orphan compositions, and Discord URL limits.
