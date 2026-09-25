# Roster implementation and local-test review

Working branch: `feat/bot-rewrite`. This document preserves local implementation and test evidence from earlier passes; PR #131 tracks publication separately. No deployment is implied.

## Current webhook publication update (2026-09-21)

This section supersedes the historical posting notes below. Bot and Dashboard posting share the API publisher, which creates or reuses an application-owned `ClashKing Rosters` webhook. The bot needs Manage Webhooks in the destination channel. Thread posts use the parent channel webhook with the thread ID.

Interactive posts have the application's refresh emoji, green Join, red Remove and a Manage link. Refresh silently redraws stored roster data, without fetching player statistics. New posts inherit the bot's guild nickname/avatar or global profile. Embed colors inherit server settings unless the roster has an integer color override. The newest interactive message becomes the saved target; name, description, image and signup changes synchronize it. Typed publication rows store channel/webhook/message IDs, never webhook tokens, and the roster's existing webhook/message fields stay aligned for automation events. Old bot-authored messages remain editable until replaced. Static final rosters use up to five separate webhook messages and do not replace the interactive target.

Dashboard signup questions have draggable ordering, up to 25 separate dropdown options, and a current-family-clans preset. Saving changed questions requires confirmation before clearing all answers. Admin answer edits use the Answers tab and are recorded in `audit_history`. One-time events store both recurrence fields as NULL; new automations use signed `event_offset_days`, resolved separately against each target roster. The scheduler SQL was tested with authoritative disposable migrations, including event-date changes and preventing duplicate one-time execution. This does not establish scheduler-to-Discord delivery in the local gateway-only stack.

Webhook execution does not support channel-message nonce deduplication. Posting is not automatically retried after ambiguous failures; inspect the channel before repeating a failed post. The automation event fields are wired, but scheduler-to-worker delivery has not been verified end to end.

## Implemented in the bot

- `/roster`: private, paginated server roster picker (15 per page), sorted by name then ID. No long slash-option form.
- Roster view: private member pages, `¹⁷Name (#TAG) | Clan` rows; answers and Discord identities are not exposed. API order is retained.
- Create button: Manage Server/Administrator only; modal asks name, clan tag and optional multiline description. Creates an empty clan roster, with clan-only signup. Family rosters and advanced settings remain Dashboard-owned.
- Join button: modal asks player tag plus configured signup questions (text, yes/no, single-select). Only verified accounts linked to the invoking Discord user can be submitted. The API rechecks ownership under a database lock and enforces clan/TH/account limits.
- Signup forms are fingerprinted; questions are reread before submission and a changed fingerprint is rejected. Four questions maximum after the player field; unsupported forms fail explicitly rather than dropping questions. User-authored question labels are kept as written. An API-side conditional questionnaire version is still needed to close the narrow race between that read and the submission transaction.
- Post button: Manage Server/Administrator only; sends a standalone snapshot with View and Join controls. View loads current API data privately. The snapshot does **not** silently claim to update itself.
- Persistent IDs carry roster UUIDs, not aliases; reads are server scoped and response IDs checked. All writes recheck permissions/actor. No custom whitelist and no in-memory interaction sessions.
- Localized bot strings in all 31 catalogs (en-GB uses en-US). Native-speaker review still useful; user-authored content is not machine-translated.
- Mentions disabled on roster messages. Mutation requests are not automatically retried; Discord posts use interaction IDs as nonces with duplicate enforcement.

## Decisions and limitations to review

| Area | Current decision / missing work |
| --- | --- |
| Permissions | Everyone allowed by native `/roster` command settings can browse/join. Create/Post additionally require native Manage Server or Administrator on every click/submission. Discord command overrides do not grant management rights to buttons. No bot whitelist restored. Dashboard authorization unchanged. |
| Posting | Snapshot plus fresh-view controls, not a synchronized board. Need a durable bot-owned publication identity and refresh/reconciliation path before automatic updates. |
| Forms | Four custom questions fit alongside player input. Labels over 45 characters or select options beyond Discord limits are explicitly rejected. Need paged durable questionnaires or a real authenticated web signup UI for larger forms. |
| Signup | Verified self accounts only. Existing signup updates answers through the canonical submission endpoint; no transfer, admin bypass or arbitrary recipient. API itself currently checks ownership but not verified status, so its stronger verification guarantee remains a cross-client review item. |
| Concurrent form edits | Bot checks a questionnaire fingerprint before posting; API validates current answer keys/types. It does not accept an expected questionnaire version, so same-ID semantic edits between read and write cannot be fenced atomically yet. |
| Creation | Name/clan/description only; no copied clan members, family mode, recurrence, limits or question editor in bot yet. These are not claimed as Python parity. |
| Member management | Self-withdrawal, manager add/remove/move, copy, delete/clear and group actions remain unimplemented in bot. Self-withdrawal needs a locked ownership-aware API mutation rather than bot read-then-delete through manager endpoints. |
| Roles | No role sync yet. Active role refresh API returns `status: ready`, `roleId`, `roleMemberUserIds`; that is an intent, not evidence of applied Discord roles. Needs bot-side permission/hierarchy checks and reconciliation. |
| Data refresh | No explicit refresh action yet. Views show stored API snapshots; joining a new account triggers API player loading. Long bulk refreshes need durable execution beyond a Worker's post-response lifetime. |
| Presentation | Compact text, not Python's configurable column renderer. Dashboard sort/column configuration is not yet interpreted by the bot. |
| Discovery | Picker pagination instead of autocomplete or typed alias search. Large-server search and player/account selection are future improvements. |
| Migration | Legacy Python `Signup_`, `RemoveMe_`, `Refresh_`, `RosterMenu_` messages are not converted by this slice. Repost with new controls for testing. |
| Replay | Posting has Discord nonce deduplication. API creation lacks a caller idempotency key; ambiguous errors tell users to inspect state before retrying. Signup is an upsert, but duplicate submissions can revise the roster again. |

## API and Dashboard findings (read-only audit)

Authoritative API files are in `clashking_api/packages/api-contracts/src/` and `workers/api/src/`.

- `bot-server.ts`: active GET `/v2/server/:serverId/rosters` (`items`) and detail (`roster`) use camelCase. Dashboard roster routes use different snake_case shapes; the bot does not mix them.
- `dashboard-roster.ts`: POST `/v2/roster?server_id=...` is the active creation contract, shared with the Dashboard.
- `dashboard-roster-extra.ts` and `dashboard-roster-runtime.ts`: active signup submissions support questions and `discordUserId`. The bot always supplies the signed actor. The API currently allows trusted bot omission of that field; consider making it mandatory for bot signup callers.
- `server-authorization.ts`: bot principals are treated as managers. Bot-side permission enforcement is mandatory for management endpoints; API authentication alone does not authorize the Discord actor.
- `roster-interaction.ts`: explicitly marked **deferred**, never include in active endpoint maps. Runtime operations/publications on disk are not a usable orchestration contract and are not called here.
- `dashboard-roster-snapshots.ts`: role refresh returns intended membership, not a completed Discord role update.
- Dashboard `app/roster/page.tsx`: public share page is labelled read-only, so it is **not** a signup fallback for oversized modal questionnaires.
- Dashboard `lib/api/clients/roster-client.ts`: existing CRUD and automation clients remain unchanged. Its task confirmed the UI manages API configuration/member/group/view/metric/refresh operations but does not publish or edit Discord roster messages. Existence of configuration endpoints/UI does not prove automations execute or keep Discord posts synchronized; scheduler and publication integration still need end-to-end verification. The separate AI builder assistant is not started for this test stack.

## Local test stack

Requested: one feature branch per repo, local API + isolated Timescale + Dashboard, no PRs or production writes. API, DevKit and Dashboard tasks own their respective setup.

| Service | Branch | Local endpoint | Verified status |
| --- | --- | --- | --- |
| Bot | `feat/bot-rewrite` | `http://127.0.0.1:8788/health` | HTTP 200, restricted dev instance running |
| API | `feat/base-link-normalization` | `http://127.0.0.1:8787/v2/health` | HTTP 200, `status: ok`; Bot env authenticated GET `/v2/links/706149153431879760` returned 200 with one local linked-account fixture. Local credential synced securely and Bot reloaded |
| Dashboard | `feat/local-roster-testing` | `http://localhost:3002` | HTTP 200; use localhost, not 127.0.0.1, for OAuth callback consistency. Roster API-client tests and typecheck passed in Dashboard task |
| Timescale | `feat/personal-armies-contract` | `127.0.0.1:54330/clashking_dev` | DevKit verified Goose 22 on isolated container `clashking-rewrite-api-dev-v2`. Backup `/private/tmp/clashking-dev-v2-pre-012-022.dump`. Port 54329 is a separate legacy lineage with 2.7M rows and was preserved; do not use or modify it for this stack |
| Dashboard assistant | not started | `http://localhost:8789` | Intentionally unavailable; moved off 8788 to avoid bot conflict |

Stable hostnames were subsequently configured; see [local tunnels](LOCAL_TUNNELS.md). Discord now points at `https://local-bot.clashk.ing/interactions`. Dashboard uses `https://local-dash.clashk.ing` and API `https://local-api.clashk.ing`; its new OAuth callback must still be appended in the Developer Portal. The original localhost callback remains supported. Real OAuth and upstream Clash dependencies are not replaced simply by running local databases. Global command registration was not changed.

Bot local config uses port 8788, API `http://127.0.0.1:8787`, and the beta Discord application. The user requested removing the temporary single-user gate on 2026-09-20, so `LOCAL_TEST_USER_ID` is now empty. Discord signature/application verification and ordinary command permissions remain enforced. The optional restriction code remains available for future opt-in testing.

Discord transport and the tunnel remain external. Whether official Clash API data/OAuth is live or stubbed is tracked separately from local database isolation. Never infer local-only data just because the bot runs under Wrangler.

## Verification / still to do

- `npm run check` passed: 164 tests across 12 files, TypeScript, lint, all 31 locale catalogs / 82 keys, four command definitions, generated env-type check and Wrangler dry-run build. This is local code proof, not live Discord proof.
- Local stack HTTP checks passed: Bot health 200, API `/v2/health` 200, bot-authenticated local link read 200, Dashboard 200. Real Bot dispatch + real local API passed roster picker, detail view and signup-modal rendering against synthetic guild `999999999999999001`; no Discord messages sent by that harness.
- API roster creation produced local `Local roster smoke` fixtures. Cross-service signup admission smoke still awaiting API task verification; synthetic guild identity cannot by itself prove live Discord membership.
- Dashboard task verified credentialed CORS (204) and unauthenticated auth endpoints (401), plus 21 roster-client and 11 auth/session tests. User must complete real Discord OAuth at `http://localhost:3002`; authenticated Dashboard roster browsing has not been claimed. Callback registration has not been changed or live reverified.
- Discord registration and actual end-user roster run: not performed yet.
- No browser/screenshot testing performed.
