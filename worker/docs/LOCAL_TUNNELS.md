# Stable local development tunnels

Created and verified 2026-09-20. No production service tunnel was modified.

| Hostname | Local origin | Exposed paths |
| --- | --- | --- |
| `https://local-bot.clashk.ing` | `http://127.0.0.1:8788` | `/interactions`, `/health` only |
| `https://local-api.clashk.ing` | `http://127.0.0.1:8787` | `/v2/*` only |
| `https://local-dash.clashk.ing` | `http://127.0.0.1:3002` | Dashboard; filesystem/editor/debug/env/git paths blocked |

Timescale remains private at `127.0.0.1:54330`; it has no public DNS/tunnel route.

Named tunnel: `clashking-local-dev`, ID `2ccfa550-fab6-4145-9a25-075cc1ada4ef`. Its three DNS CNAME records were created without overwriting existing records. Configuration is `worker/cloudflared.local.yml`; certificate and connector credentials stay in the user's `.cloudflared` directory, outside Git.

## Run

From the Bot's `worker` directory, run the bot and connector in separate terminals:

```sh
npm run dev
cloudflared tunnel --config cloudflared.local.yml --no-autoupdate run clashking-local-dev
```

Keep the API and Dashboard processes running in their own repositories. Dashboard uses its `npm run dev:tunnel` configuration. Stop each process with Ctrl-C in its terminal; stopping the connector leaves the stable DNS names intact but unavailable. No login/startup daemon was installed. The Mac must remain awake and connected.

## Authentication boundaries

- Bot still calls the **loopback API**, not the public API hostname. The temporary single-user restriction is disabled for beta testing; Discord signature verification and normal command permissions remain required.
- The API task removed its matching temporary single-user restriction and restarted the API. Bot bearer authentication and ordinary user authentication remain separate; unauthenticated `/v2/auth/me` still returns 401.
- API private data still requires authentication. Deliberately public `/v2` contracts (e.g. health/static/public Clash data and auth entrypoints) remain public; this tunnel does not add Cloudflare Access in front of them.
- Refresh cookies are host-only, Secure, HttpOnly, SameSite=None; local-api does not overwrite production API host-only cookies.
- API allows credentialed CORS from `https://local-dash.clashk.ing`, retaining localhost support.
- Wrangler's `/cdn-cgi/local/*` and non-v2 API routes are not exposed. Dashboard task added exact host checks, filesystem-deny rules and disabled its inspector. Tunnel additionally blocks `__debug` and filesystem/editor/env/git paths.

## Discord application configuration

Local application: **ClashKing Beta**, `808566437199216691`. The bot's ignored `.dev.vars` and command-registration `.env.dev` use its credentials. Dashboard and App use its public OAuth client ID, never its bot token.

Beta's interaction endpoint is **`https://local-bot.clashk.ing/interactions`**. Discord accepted its signature-validation handshake and readback confirmed the endpoint. Its global commands were synchronized to `/link`, `/unlink`, `/base`, and `/roster`. The user reports removing the temporary local endpoint from the production application; this beta switch did not edit production.

The API's beta OAuth client secret and bot token are in the separate macOS Keychain service `ing.clashking.effect-rewrite.local-api`, account `discord-beta-oauth-v1`. The production credential profile was preserved. The API launcher requires beta credentials rather than falling back to production.

**Remaining user action:** In **ClashKing Beta's** Discord Developer Portal, OAuth2 → Redirects, register the exact callbacks needed:

```text
https://local-dash.clashk.ing/auth/callback
clashking://com.clashking.clashkingapp/oauth
```

The beta redirect list was empty on live readback. The documented bot-authenticated application-edit endpoint does not expose redirect-URI editing. App web testing additionally needs its actual launcher callback registered; do not assume a `local-app` tunnel exists from this document. No authenticated Dashboard/App login is claimed until the callbacks are registered and the user signs in.

The Tracking task verified a real beta Discord gateway running against isolated Timescale `127.0.0.1:54330/clashking_dev` and local Valkey. It persists only test guild `1317858645349765150` (ClashKing Dev), with a healthy shard heartbeat and complete guild/member metadata. The API task independently verified the live cache. This guild scope is separate from the removed user restriction. No collectors or delivery workers were started, and no production metadata or fake heartbeat was copied.

## Verified

- External HTTPS 200: Bot health, API `/v2/health`, Dashboard root.
- External unauthenticated roster data: HTTP 401.
- API/Bot explorer paths, Dashboard `__debug` and `@fs` paths: HTTP 404.
- Dashboard task verified external credentialed CORS (204), served API origin `https://local-api.clashk.ing`, and HMR WebSocket upgrade (101).
- Discord endpoint PATCH accepted; GET readback matched the stable hostname.
- Beta global commands registered; no production command registration, deployment, push or PR performed.

References: [Cloudflare local tunnel configuration](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/configuration-file/), [Discord application editing](https://docs.discord.com/developers/resources/application#edit-current-application).
