# ClashKing Bot

ClashKing Bot is being migrated to a Cloudflare Workers, TypeScript, and Effect application. The active runtime lives in [`worker`](worker); the preserved Python/disnake implementation lives in [`archived/python`](archived/python) and is excluded from every active build and deployment.

The first production slice implements `/base`, `/link`, `/unlink`, and their persistent base/link components. It uses Discord's signed HTTP interactions, delegates business persistence to the ClashKing API, and keeps runtime dependencies behind an Effect service layer.

```sh
cd worker
npm ci
npm run check
```

Command registration and deployment are intentionally separate, explicit operations. Do not run `register:*` or `deploy:*` from CI or routine validation.
