# Local development tunnels

The dedicated Beta application uses the local stack. The managed tunnel maps:

| Hostname | Local origin | Exposed paths |
| --- | --- | --- |
| `local-bot.clashk.ing` | `http://127.0.0.1:8788` | `/interactions`, `/health` |
| `local-api.clashk.ing` | `http://127.0.0.1:8787` | `/v2/*` |
| `local-ai.clashk.ing` | `http://127.0.0.1:8789` | `/chat`, `/health` |
| `local-dash.clashk.ing` | `http://127.0.0.1:3002` | Dashboard |

Use the existing managed connector instead of starting a duplicate. The
repository's fallback configuration is `worker/cloudflared.local.yml`.
Credentials remain outside Git. Timescale has no public tunnel route.

Run `npm run dev` from `worker` and the API/Dashboard from their own repositories.
The Bot calls the loopback API even when Discord reaches it through the tunnel.
Keep signature verification, service authentication, and normal user/server
permissions enabled. The tunnel does not replace application authorization.

Beta is application `808566437199216691`. Verify its current interaction endpoint,
OAuth redirect configuration, and registered command list before an authorized
Discord test. Historical setup evidence is not proof of current configuration.
Never switch the production application's endpoint for local testing.

The Dashboard's tunnel mode is `npm run dev:tunnel`. Its browser origin and the
API's credentialed CORS allowlist must match. API cookies are host-only, so local
API credentials do not replace production cookies. Keep inspector, filesystem,
environment, and Git paths blocked at the tunnel and development server.

Stopping the local connector leaves the DNS names configured but unavailable.
No local build or tunnel health check proves real Discord delivery or OAuth.
