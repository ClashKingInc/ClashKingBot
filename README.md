# ClashKing Bot

ClashKing Bot receives Discord interactions through a Cloudflare Worker written
in TypeScript and Effect. The active application is in [`worker`](worker).
The ClashKing API owns authorization and application persistence; Tracking
owns the Discord gateway and background delivery.

Server configuration lives in the Dashboard. The bot provides member commands,
reports, and persistent message controls. The retired Python runtime is available
in Git history and is no longer part of this repository's runtime or tooling.

## Development

Use Node 24 or newer, then run:

```sh
cd worker
npm ci
npm run check
```

The check validates locales, command definitions, generated types, lint,
TypeScript, and a Wrangler dry-run build. See the [Worker guide](worker/README.md)
for local configuration and release boundaries, and [local service checks](tooling/e2e/README.md)
for end-to-end verification.

Command registration replaces Discord's global command list. Registration and
Worker deployment are separate release operations, never routine validation.
