# First-slice compatibility and blockers

This file compares the archived Python behavior with the Worker implementation. “Implemented” means the code path and focused tests exist; it does not mean production Discord registration or deployment occurred.

| Surface | Python compatibility reference | Worker status |
| --- | --- | --- |
| `/base` | `base_link`, `description`, `photo`; `&&` becomes a newline; rejects non-layout links | Implemented end to end with the current API upload/create contracts. The API limits descriptions to 1,000 characters, so the Worker truncates at 1,000 rather than Python's 1,900. |
| Base Link button | Increments the count and privately returns a normalized layout link | Implemented with `POST /v2/bases/:baseId/downloaders/:userId`; the API makes repeat clicks by one user idempotent, improving the legacy duplicate count. |
| Base download history | Privately lists downloader mentions | Implemented from the server-owned base response. |
| `/link` | `player`, `user?`, `api_token?`, `greet?`; self-link disables greeting; token may be required by server; privileged users can mod-link | Core link, transfer verification, full-whitelist/Manage Server checks, and server token policy are implemented against current API contracts. Role/nickname refresh and greetings remain blocked below. |
| Link button/modal/help | Persistent buttons collect player tag and optional token | Implemented with stable `ck:link:*` IDs that survive isolate replacement. |
| `/unlink` | Owners can unlink; privileged users may unlink another owner subject to membership/family checks | Self-unlink is implemented. Privileged cross-user unlink is blocked because the bot API cannot resolve a player tag to its current owner with the legacy authorization context. |

## Required external follow-ups

No external repository was changed by this branch.

1. **API — atomic post-link evaluation contract.** Add a bot-authenticated endpoint such as `POST /v2/server/:serverId/members/:userId/evaluate` with `{ "reason": "account_linked", "playerTag": "#TAG" }`. It should return the applied role/nickname changes and safe display rows. Without it the Worker can persist `/link`, but cannot reproduce the Python role/nickname refresh without duplicating business rules or writing Discord state directly.
2. **API — greeting resolution/delivery contract.** Add a bot-authenticated, idempotent operation keyed by interaction id that resolves the linked player's family clan, the server's configured greeting template/channel, and either delivers the greeting or returns a complete Discord payload. Required result fields are `{ delivered, channelId?, reason? }`. The existing link endpoint has no server id or greeting intent, so it cannot safely own this side effect today.
3. **API — privileged unlink authorization.** Add a server-scoped bot endpoint such as `DELETE /v2/server/:serverId/links/:playerTag` with `{ actorId }`, or a read contract that returns the current owner plus family/member authorization facts. It must enforce the legacy rules server-side and return the unlinked player identity. The existing `DELETE /v2/links/:userId/:playerTag` requires the Worker to already know the owner.
4. **API — command-specific whitelist parity.** The Worker can honor Discord Manage Server and `full_whitelist_role`, but the current API contract does not expose the legacy per-command `/whitelist` decision for `link`/`unlink`. Either expose a bot authorization decision (`allowed`, `source`) or formally retire command-specific entries.
5. **API — base creation ownership.** Current base creation posts the Discord message inside the API, after which the Worker patches in buttons. For atomic component parity, extend `CreateBaseRequest` with the stable component payload or add a bot-only persist-from-interaction contract with compensation semantics. Today a Discord PATCH failure can leave a valid persisted base message without buttons.
6. **API/Assets — description and image boundary.** Python accepted 1,900 description characters and reused the original Discord attachment; the current API accepts 1,000 characters and requires a `cdn.clashk.ing` upload. Keep the safer current contract or explicitly raise the API limit after product review; the Worker must not bypass CDN ownership.
7. **Discord/Cloudflare operations.** Provision separate dev/prod Discord applications and Cloudflare secrets, set the Interactions Endpoint URL to `/interactions`, then register the three definitions in dev before production. These are operational steps, not repository changes, and were deliberately not performed here.
