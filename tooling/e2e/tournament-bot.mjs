// Called by the real local competitive API harness while its scoped records
// and isolated credentials exist. Discord delivery alone is a loopback sink.
import { createRequire } from 'node:module';
import { generateKeyPairSync, sign } from 'node:crypto';
import assert from 'node:assert/strict';
import { bundleWorker } from './bundle-worker.mjs';
const require = createRequire(new URL('../../worker/package.json', import.meta.url));
const { Miniflare, convertV4MiniflareOptions } = require('miniflare');

export async function verifyTournamentBot({ apiOrigin, apiToken, serverId, tournamentId, tournamentName }) {
  const api = new URL(apiOrigin);
  assert(api.protocol === 'http:' && api.hostname === '127.0.0.1', 'Only loopback verification is allowed');
  const { publicKey, privateKey } = generateKeyPairSync('ed25519');
  const publicHex = publicKey.export({ type: 'spki', format: 'der' }).subarray(-32).toString('hex');
  const applicationId = '999999999999993401', responses = new Map();
  let counter = 999999999999993500n;
  const bot = new Miniflare(convertV4MiniflareOptions({ host: '127.0.0.1', port: 0, workers: [{
    name: 'tournament-bot-e2e', ...await bundleWorker(), compatibilityDate: '2026-08-22', compatibilityFlags: ['nodejs_compat'],
    bindings: { APP_ENV: 'dev', LOCAL_TEST_USER_ID: '', DASHBOARD_BASE_URL: 'https://local-dash.clashk.ing',
      CLASHKING_API_BASE_URL: apiOrigin, CLASHKING_API_TOKEN: apiToken, DISCORD_APPLICATION_ID: applicationId,
      DISCORD_BOT_TOKEN: `${Buffer.from(applicationId).toString('base64')}.local.token`, DISCORD_PUBLIC_KEY: publicHex },
    outboundService: async request => {
      const url = new URL(request.url);
      if (url.origin === api.origin) return fetch(request.url, { method: request.method, headers: Object.fromEntries(request.headers),
        ...(['GET', 'HEAD'].includes(request.method) ? {} : { body: await request.arrayBuffer() }) });
      if (url.hostname === 'discord.com' && request.method === 'PATCH' && url.pathname.includes('/messages/@original')) {
        responses.set(url.pathname.split('/')[5], await request.json()); return Response.json({ id: '999999999999993499' });
      }
      throw Error('Unexpected outbound request in tournament E2E');
    },
  }] }));
  const interactionOrigin = new URL('/interactions', String(await bot.ready));
  async function interact(action, options = [], who = '999999999999993402', type = 2, guildId = serverId) {
    const token = String(counter++);
    const body = JSON.stringify({ id: token, application_id: applicationId, guild_id: guildId,
      member: { user: { id: who, username: 'Local reader' }, roles: [], permissions: '0' },
      channel_id: '999999999999993403', version: 1, token, type, data: { name: 'tournament', options: [{ name: action, type: 1, options }] } });
    const timestamp = String(Math.floor(Date.now() / 1000));
    const response = await fetch(interactionOrigin, { method: 'POST', headers: { 'Content-Type': 'application/json',
      'X-Signature-Timestamp': timestamp, 'X-Signature-Ed25519': sign(null, Buffer.from(timestamp + body), privateKey).toString('hex') }, body });
    assert.equal(response.status, 200);
    const initial = await response.json();
    if (![5, 6].includes(initial.type)) return initial.data;
    for (let i = 0; i < 160; i++) { if (responses.has(token)) return responses.get(token); await new Promise(r => setTimeout(r, 50)); }
    throw Error('Deferred tournament command did not complete');
  }
  try {
    const browse = await interact('browse');
    assert(JSON.stringify(browse).includes(tournamentName), `Browse result: ${JSON.stringify(browse)}`);
    assert(JSON.stringify(browse).includes('Free entry'));
    assert(JSON.stringify(browse).includes('local-app.clashk.ing/tournaments'));
    const detail = await interact('view', [{ name: 'tournament', type: 3, value: tournamentId }]);
    assert(JSON.stringify(detail).includes(tournamentName));
    assert(!JSON.stringify(detail).includes('Secret'), 'Never expose management labels');
    const otherReader = await interact('view', [{ name: 'tournament', type: 3, value: tournamentId }], '999999999999993404');
    assert(JSON.stringify(otherReader).includes(tournamentName), 'Public lookups must not be invoker-owned');
    const foreignScope = await interact('view', [{ name: 'tournament', type: 3, value: tournamentId }], undefined, 2, '999999999999993405');
    assert(JSON.stringify(foreignScope).includes('this server'));
    return { checks: ['signed HTTP browse', 'deferred detail', 'free entry', 'Beta app links', 'public second reader', 'server scope', 'internal labels hidden'], externalDiscordSends: 0 };
  } finally { await bot.dispose(); }
}
