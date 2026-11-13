// Signed HTTP interactions through the actual Bot Worker. API and Discord are
// loopback HTTP boundary fixtures; the separate API E2E covers persistence/auth.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { generateKeyPairSync, sign } from 'node:crypto';
import { createRequire } from 'node:module';
import { bundleWorker } from './bundle-worker.mjs';
const require = createRequire(new URL('../../worker/package.json', import.meta.url));
const { Miniflare, convertV4MiniflareOptions } = require('miniflare');
const app = '999999999999996501', actor = '999999999999996502', guild = '999999999999996510';
const preparation = '11111111-2222-4333-8444-555555555555';
const panel = '11111111-2222-4333-8444-555555555556';
const button = '11111111-2222-4333-8444-555555555557';
const commandId = '999999999999996599';
const { publicKey, privateKey } = generateKeyPairSync('ed25519');
const publicHex = publicKey.export({ type: 'spki', format: 'der' }).subarray(-32).toString('hex');
const calls = [], webhooks = [];
let linked = false, rejectToken = false, ticketFailure;
const provider = createServer(async (request, response) => {
  try {
    let raw = ''; for await (const chunk of request) raw += chunk;
    const body = raw ? JSON.parse(raw) : undefined;
    const path = new URL(request.url, 'http://fixture').pathname;
    calls.push({ method: request.method, path, body });
    const json = (value, status = 200) => { response.writeHead(status, { 'Content-Type': 'application/json' }); response.end(JSON.stringify(value)); };
    if (ticketFailure && path === ticketFailure.path) return json({ code: 'conflict', message: ticketFailure.message }, 409);
    if (path === '/v2/bot/server-activity') return json({ accepted: true });
    if (path === `/v2/links/${actor}` && request.method === 'GET') return json({ items: linked ? [{ player_tag: '#PYLQ', is_verified: true }] : [] });
    if (path === `/v2/links/${actor}` && request.method === 'POST') {
      assert.equal(body.player_tag, '#PYLQ'); assert.equal(body.api_token, rejectToken ? 'bad' : 'fixture');
      if (rejectToken) return json({ message: 'Invalid token' }, 403);
      linked = true; return json({ account: { tag: '#PYLQ', is_verified: true } });
    }
    if (path === '/v2/runtime/tickets/open/prepare') return json({ outcome: 'link_required', content: 'Link an account to continue this ticket application.', link: { customId: `ck:ticket:link:${preparation}`, label: 'Link an account' } });
    if (path === '/v2/runtime/tickets/resume') {
      assert.equal(JSON.parse(body.interaction.rawBody).data.custom_id, `ck:ticket:resume:${preparation}`);
      return json({ outcome: 'ready', form: { kind: 'modal', customId: 'ck:ticket:answers:' + preparation, title: 'Application', fields: [{ customId: 'answer', label: 'Answer', required: true, style: 'short', maxLength: 100 }] } });
    }
    if (path === `/api/v10/applications/${app}/commands`) return json([{ id: commandId, application_id: app, name: 'link', description: 'Link accounts', type: 1, version: commandId }]);
    if (path.endsWith('/emojis')) return json({ items: [] });
    if (path.includes('/webhooks/')) {
      webhooks.push({ path, method: request.method, body });
      if (request.method === 'DELETE') { response.writeHead(204); return response.end(); }
      return json({ id: '999999999999996900', ...body });
    }
    throw Error(`Unexpected fixture request ${request.method} ${path}`);
  } catch (error) { response.writeHead(500); response.end(String(error)); }
});
await new Promise((resolve) => provider.listen(0, '127.0.0.1', resolve));
const providerOrigin = `http://127.0.0.1:${provider.address().port}`;
let worker;
try {
  worker = new Miniflare(convertV4MiniflareOptions({ host: '127.0.0.1', port: 0, workers: [{
    name: 'ticket-link-e2e', ...await bundleWorker(), compatibilityDate: '2026-08-22', compatibilityFlags: ['nodejs_compat'],
    bindings: { APP_ENV: 'dev', LOCAL_TEST_USER_ID: actor, DASHBOARD_BASE_URL: 'https://dash.clashk.ing', CLASHKING_API_BASE_URL: providerOrigin,
      CLASHKING_API_TOKEN: 'fixture', DISCORD_APPLICATION_ID: app, DISCORD_BOT_TOKEN: `${Buffer.from(app).toString('base64')}.local.token`, DISCORD_PUBLIC_KEY: publicHex },
    outboundService: async (request) => {
      const url = new URL(request.url);
      assert(url.origin === providerOrigin || url.hostname === 'discord.com', 'No external network permitted');
      return fetch(providerOrigin + url.pathname + url.search, { method: request.method, headers: request.headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer() });
    },
  }] }));
  const origin = new URL('/interactions', String(await worker.ready));
  let counter = 999999999999996700n;
  const wait = async (read) => { for (let i = 0; i < 100; i++) { const value = read(); if (value) return value; await new Promise((resolve) => setTimeout(resolve, 25)); } throw Error('Deferred response missing'); };
  const interact = async (data) => {
    const token = String(counter++), timestamp = String(Math.floor(Date.now() / 1000));
    const raw = JSON.stringify({ id: token, application_id: app, guild_id: guild, channel_id: '999999999999996511', member: { user: { id: actor, username: 'Fixture' }, roles: [], permissions: '0' }, version: 1, token, locale: 'en-US', ...data });
    const response = await fetch(origin, { method: 'POST', body: raw, headers: { 'Content-Type': 'application/json', 'X-Signature-Timestamp': timestamp, 'X-Signature-Ed25519': sign(null, Buffer.from(timestamp + raw), privateKey).toString('hex') } });
    assert.equal(response.status, 200); return { initial: await response.json(), token };
  };
  const empty = await interact({ type: 2, data: { name: 'link', options: [{ name: 'list', type: 1 }] } });
  assert.equal(empty.initial.type, 5);
  const privateReply = await wait(() => webhooks.find((item) => item.method === 'POST' && item.path.includes(empty.token) && item.body?.flags === 64));
  assert(privateReply.body.embeds[0].description.includes(`</link add:${commandId}>`));
  await wait(() => webhooks.find((item) => item.method === 'DELETE' && item.path.includes(empty.token)));
  const open = await interact({ type: 3, data: { custom_id: `ck:ticket:open:${panel}:${button}`, component_type: 2 }, message: { id: '999999999999996512' } });
  const linkId = open.initial.data.components[0].components[0].custom_id;
  assert.equal(linkId, `ck:link:start:ticket:${preparation}`);
  const modal = await interact({ type: 3, data: { custom_id: linkId, component_type: 2 } });
  assert.equal(modal.initial.type, 9);
  assert.equal(modal.initial.data.custom_id, `ck:link:submit:ticket:${preparation}`);
  const submit = async (token) => interact({ type: 5, data: { custom_id: modal.initial.data.custom_id, components: [{ type: 1, components: [{ type: 4, custom_id: 'player', value: '#PYLQ' }] }, { type: 1, components: [{ type: 4, custom_id: 'api_token', value: token }] }] } });
  rejectToken = true;
  const invalid = await submit('bad');
  const retry = await wait(() => webhooks.find((item) => item.path.includes(invalid.token) && item.body?.components));
  assert.equal(retry.body.components[0].components[0].custom_id, linkId);
  rejectToken = false;
  const success = await submit('fixture');
  const reply = await wait(() => webhooks.find((item) => item.path.includes(success.token) && item.body?.components));
  assert.equal(reply.body.components[0].components[0].custom_id, `ck:ticket:resume:${preparation}`);
  const resume = await interact({ type: 3, data: { custom_id: `ck:ticket:resume:${preparation}`, component_type: 2 } });
  assert.equal(resume.initial.type, 9); assert.equal(resume.initial.data.title, 'Application');
  assert.equal(calls.filter((call) => call.method === 'POST' && call.path === `/v2/links/${actor}`).length, 2);
  const failures = [
    ['Ticket answers exceed the durable snapshot limit', 'Answers too long', 'use shorter answers', true],
    ['Ticket questionnaire exceeds the durable answer limit', 'Ticket panel needs attention', 'reduce them in the dashboard', false],
    ['Ticket configuration exceeds the runtime snapshot limit', 'Ticket panel needs attention', 'simplify it in the dashboard', false],
    ['Ticket form replay journal is full', 'Restart the application', 'Start again from the ticket panel', true],
  ];
  for (const [message, title, instruction, advancing] of failures) {
    ticketFailure = { path: advancing ? `/v2/runtime/ticket-operations/${preparation}/advance` : '/v2/runtime/tickets/open/prepare', message };
    const result = await interact(advancing
      ? { type: 5, data: { custom_id: `ck:ticket:answers:${preparation}:0`, components: [] } }
      : { type: 3, data: { custom_id: `ck:ticket:open:${panel}:${button}`, component_type: 2 }, message: { id: '999999999999996512' } });
    assert.equal(result.initial.type, 4);
    assert.equal(result.initial.data.flags, 64);
    assert.equal(result.initial.data.embeds[0].title, title);
    assert(result.initial.data.embeds[0].description.includes(instruction));
    if (advancing) assert(result.initial.data.embeds[0].description.includes('Your application was not submitted.'));
  }
  ticketFailure = { path: '/v2/runtime/tickets/open/prepare', message: 'Untrusted provider detail: do not expose' };
  const unknown = await interact({ type: 3, data: { custom_id: `ck:ticket:open:${panel}:${button}`, component_type: 2 }, message: { id: '999999999999996512' } });
  assert.equal(unknown.initial.data.embeds[0].title, 'This item changed');
  assert(!JSON.stringify(unknown.initial).includes('Untrusted provider detail'));
  console.log('PASS actual Bot Worker HTTP: signed empty link list, private embed + registered mention + public cleanup, ticket link modal, invalid-token retry, verified link, continuation modal, actionable known ticket size errors and unknown-error redaction. Boundary providers are local fixtures; no external writes.');
} finally { await worker?.dispose(); await new Promise((resolve) => provider.close(resolve)); }
