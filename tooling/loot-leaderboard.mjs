import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync, unlinkSync, openSync, closeSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { randomUUID } from 'node:crypto';
import { loadWorkspace, clashProxyOrigin, inheritedEnvironment } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';

export const CLAN_TAG = '#P09LP8CY';
export const GUILD_ID = '1315502785831374848';
export const CHANNEL_ID = '1400294002724438236';
export const INTERVAL_MS = 30_000;
const scriptPath = fileURLToPath(import.meta.url);
const stateDir = join(dirname(scriptPath), '../.local/loot-leaderboard');
const statePath = join(stateDir, 'state.json');
const lockPath = join(stateDir, 'process.json');
const logPath = join(stateDir, 'run.log');
const title = 'HellinaHelmet · Top Looters';
const resourceEmoji = { gold: '<:gold:1320621687108272159>', elixir: '<:elixir:1320621680032481281>', darkElixir: '<:dark_elixir:1320621672570683475>' };
const readJSON = path => existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : null;
function saveState(value) {
  writeFileSync(`${statePath}.next`, JSON.stringify(value, null, 2), { mode: 0o600 });
  renameSync(`${statePath}.next`, statePath);
}
function alive(pid) {
  try { process.kill(pid, 0); return true; } catch (error) { return error.code === 'EPERM'; }
}

export function trackingWindow(countingFrom, now = new Date()) {
  const start = new Date(countingFrom);
  if (!countingFrom || !Number.isFinite(start.getTime()) || start > now) throw Error('Invalid leaderboard start time');
  return { start, end: now };
}

export function initializeCountingFrom(state, now = Date.now()) {
  const countingFrom = state?.countingFrom ?? new Date(state?.creatingAt ?? now).toISOString();
  trackingWindow(countingFrom, new Date(now));
  return { ...state, countingFrom };
}

// Sessions are a timestamp-based estimate: consecutive attacks no more than
// three minutes apart belong together. Include the final attack's duration,
// but never add a trailing three-minute allowance or count overlapping spans twice.
export function farmingSessions(attacks) {
  const ordered = attacks.map(attack => ({ at: Date.parse(attack.at), duration: Number(attack.duration) }))
    .sort((a, b) => a.at - b.at);
  if (ordered.some(attack => !Number.isFinite(attack.at) || !Number.isFinite(attack.duration) || attack.duration < 0)) {
    throw Error('Invalid attack timing for farming sessions');
  }
  let count = 0, total = 0, start = 0, end = 0, previous = 0;
  for (const attack of ordered) {
    if (count === 0 || attack.at - previous > 180_000) {
      if (count > 0) total += end - start;
      count++;
      start = attack.at;
      end = attack.at + attack.duration * 1000;
    } else {
      end = Math.max(end, attack.at + attack.duration * 1000);
    }
    previous = attack.at;
  }
  if (count > 0) total += end - start;
  return { sessionCount: count, sessionSeconds: String(Math.round(total / 1000)) };
}

// Matches the Dashboard's loot metric: farming attack gold + elixir + dark elixir.
// Membership comes from the current Clash roster, not stale basic_clan.members.
export async function loadLeaderboard(pool, roster, countingFrom, now = new Date()) {
  if (roster.tag !== CLAN_TAG || !Array.isArray(roster.memberList) || roster.memberList.length === 0) {
    throw Error('The current HellinaHelmet roster is unavailable');
  }
  const members = [...new Map(roster.memberList.map(m => [m.tag, m])).values()];
  if (members.some(m => typeof m.tag !== 'string' || typeof m.name !== 'string') || members.length > 50) {
    throw Error('Invalid clan roster');
  }
  const { start, end } = trackingWindow(countingFrom, now);
  const result = await pool.query(`
    SELECT player_tag, sum(
      COALESCE((looted_resources->>'gold')::bigint,0) +
      COALESCE((looted_resources->>'elixir')::bigint,0) +
      COALESCE((looted_resources->>'darkElixir')::bigint,0)
    )::text AS loot, count(*)::int AS attacks,
    COALESCE(sum(duration_seconds) FILTER (WHERE duration_seconds > 0),0)::text AS farming_seconds,
    count(*) FILTER (WHERE duration_seconds > 0)::int AS timed_attacks,
    jsonb_agg(jsonb_build_object('at',battle_time,'duration',duration_seconds) ORDER BY battle_time) AS attack_timings,
    sum(COALESCE((looted_resources->>'gold')::bigint,0))::text AS gold,
    sum(COALESCE((looted_resources->>'elixir')::bigint,0))::text AS elixir,
    sum(COALESCE((looted_resources->>'darkElixir')::bigint,0))::text AS dark_elixir
    FROM battles_farming
    WHERE player_tag=ANY($1::text[]) AND battle_time >= $2 AND battle_time < $3
    GROUP BY player_tag`, [members.map(m => m.tag), start, end]);
  const totals = new Map(result.rows.map(row => [row.player_tag, row]));
  return members.map(m => ({ tag: m.tag, name: m.name, loot: totals.get(m.tag)?.loot ?? '0', attacks: totals.get(m.tag)?.attacks ?? 0,
    ...farmingSessions(totals.get(m.tag)?.attack_timings ?? []),
    farmingSeconds: totals.get(m.tag)?.farming_seconds ?? '0', timedAttacks: totals.get(m.tag)?.timed_attacks ?? 0,
    gold: totals.get(m.tag)?.gold ?? '0', elixir: totals.get(m.tag)?.elixir ?? '0', darkElixir: totals.get(m.tag)?.dark_elixir ?? '0' }))
    .filter(row => BigInt(row.loot) > 0n)
    .sort((a, b) => BigInt(a.loot) === BigInt(b.loot) ? a.tag.localeCompare(b.tag) : BigInt(a.loot) > BigInt(b.loot) ? -1 : 1)
    .slice(0, 5);
}

function safeName(name) {
  return name.replace(/[\r\n\t\u0000-\u001f]/g, ' ').replace(/([\\`*_{}\[\]()<>~|])/g, '\\$1');
}
export function formatFarmingTime(seconds) {
  const value = BigInt(seconds);
  const hours = value / 3600n;
  const minutes = (value % 3600n) / 60n;
  const remainder = value % 60n;
  return [hours > 0n ? `${hours}h` : '', minutes > 0n ? `${minutes}m` : '', remainder > 0n || value === 0n ? `${remainder}s` : ''].filter(Boolean).join(' ');
}
const lootNumberFormat = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 });
export const formatLoot = value => lootNumberFormat.format(BigInt(value));

export function messagePayload(rows, countingFrom, now = new Date()) {
  const { start } = trackingWindow(countingFrom, now);
  const average = (numerator, denominator) => denominator > 0n
    ? formatLoot((numerator + denominator / 2n) / denominator) : '—';
  const fields = rows.map((row, index) => {
    const loot = BigInt(row.loot);
    const farmingSeconds = BigInt(row.farmingSeconds ?? 0);
    const completeTiming = row.attacks > 0 && row.timedAttacks === row.attacks && farmingSeconds > 0n;
    // Missing/zero durations must not silently inflate the rate by shortening its denominator.
    const sessionSeconds = BigInt(row.sessionSeconds ?? 0);
    const perMinute = completeTiming ? average(loot * 60n, sessionSeconds) : '—';
    const perAttack = average(loot, BigInt(row.attacks));
    const farmingTime = completeTiming ? formatFarmingTime(sessionSeconds) : 'Incomplete attack durations';
    const avgDuration = completeTiming ? formatFarmingTime((farmingSeconds + BigInt(row.attacks) / 2n) / BigInt(row.attacks)) : '—';
    const value = [
      `**${formatLoot(loot)}** total loot · **${row.attacks}** attacks`,
      `${resourceEmoji.gold} **${formatLoot(row.gold ?? 0)}** · ${resourceEmoji.elixir} **${formatLoot(row.elixir ?? 0)}** · ${resourceEmoji.darkElixir} **${formatLoot(row.darkElixir ?? 0)}**`,
      `**${perMinute}** / farming min · **${perAttack}** / attack`,
      `Farmed **${farmingTime}** · Avg attack **${avgDuration}**`,
    ].join('\n') + (index < rows.length - 1 ? '\n\u200b' : '');
    return { name: `${index + 1}. ${safeName(row.name)}`, value, inline: false };
  });
  const description = `Started <t:${Math.floor(start.getTime() / 1000)}:f>` + (fields.length ? '' : '\nNo loot recorded since the start yet.');
  return { content: '', attachments: [], allowed_mentions: { parse: [] }, embeds: [{ title, description, fields, color: 0xe6ac46,
    footer: { text: 'Farming sessions use a 3-minute gap · Updates every 30 seconds' },
    timestamp: now.toISOString() }] };
}

export function discordRequestBody(body, file) {
  if (!file) return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  const payload = { ...body, attachments: [{ id: 0, filename: file.name, description: 'Top-five attack loot histograms; common 500,000-loot bins; percentage of each player’s attacks.' }],
    embeds: body.embeds.map((embed, i) => i === 0 ? { ...embed, image: { url: `attachment://${file.name}` } } : embed) };
  const form = new FormData();
  form.append('payload_json', JSON.stringify(payload));
  form.append('files[0]', new Blob([file.bytes], { type: 'image/png' }), file.name);
  return { headers: {}, body: form };
}

class DiscordError extends Error {
  constructor(status) { super(`Discord request failed (${status})`); this.status = status; }
}
async function discord(token, path, method = 'GET', body, file) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const request = body ? discordRequestBody(body, file) : { headers: {} };
    const response = await fetch(`https://discord.com/api/v10${path}`, {
      ...request, method, headers: { Authorization: `Bot ${token}`, ...request.headers }, signal: AbortSignal.timeout(15_000),
    });
    if (response.status === 429) {
      const data = await response.json();
      await sleep(Math.max(1000, Math.min(Number(data.retry_after) * 1000 || 1000, 60_000)));
      continue;
    }
    if (!response.ok) throw new DiscordError(response.status);
    return response.status === 204 ? null : response.json();
  }
  throw Error('Discord rate limit did not clear');
}

export async function publishMessage(api, state, payload, persist, botId, now = Date.now(), file) {
  if (state?.channelId && state.channelId !== CHANNEL_ID) throw Error('Saved message belongs to another channel');
  state ??= { channelId: CHANNEL_ID };
  if (!state.messageId) {
    if (!state.nonce) {
      state = { ...state, nonce: randomUUID().replaceAll('-', '').slice(0, 24), creatingAt: now };
      persist(state); // Persist before POST so retries use Discord's deduplicating nonce.
    } else {
      const recent = await api(`/channels/${CHANNEL_ID}/messages?limit=100`);
      const previous = recent.find(m => m.author.id === botId && String(m.nonce) === state.nonce);
      if (previous) state = { ...state, messageId: previous.id };
      else if (now - state.creatingAt > 120_000) throw Error('Uncertain initial send; inspect channel and recover message ID before restarting');
    }
    if (!state.messageId) {
      const message = await api(`/channels/${CHANNEL_ID}/messages`, 'POST', { ...payload, nonce: state.nonce, enforce_nonce: true }, file);
      state = { ...state, messageId: message.id };
    }
    persist(state);
  }
  await api(`/channels/${CHANNEL_ID}/messages/${state.messageId}`, 'PATCH', payload, file);
  state = { ...state, updatedAt: new Date(now).toISOString() };
  persist(state);
  return state;
}

async function run(preview = false) {
  const workspace = loadWorkspace('/Users/matthewanderson/ClashKing');
  const require = createRequire(join(workspace.config.repositories.api, 'package.json'));
  const { Pool } = require('pg');
  const pool = new Pool({ host: workspace.env.TIMESCALE_HOST, port: Number(workspace.env.TIMESCALE_PORT),
    database: workspace.env.TIMESCALE_DATABASE, user: workspace.env.TIMESCALE_USERNAME,
    password: workspace.env.TIMESCALE_PASSWORD, max: 1, connectionTimeoutMillis: 5000, statement_timeout: 10_000 });
  let stop = false;
  const abort = new AbortController();
  const shutdown = () => { stop = true; abort.abort(); };
  process.once('SIGTERM', shutdown); process.once('SIGINT', shutdown);
  let locked = false;
  try {
    if (!preview) {
      const previous = readJSON(lockPath);
      if (previous && alive(previous.pid)) throw Error('Leaderboard is already running');
      if (previous) unlinkSync(lockPath);
      const fd = openSync(lockPath, 'wx', 0o600);
      writeFileSync(fd, JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() })); closeSync(fd); locked = true;
    }
    const token = workspace.env.DISCORD_BOT_TOKEN;
    const api = (path, method, body, file) => discord(token, path, method, body, file);
    let botId;
    if (!preview) {
      const channel = await api(`/channels/${CHANNEL_ID}`);
      if (channel.guild_id !== GUILD_ID || channel.type !== 0) throw Error('Unexpected Discord channel');
      botId = (await api('/users/@me')).id;
      const saved = readJSON(statePath);
      if (saved?.messageId) {
        const message = await api(`/channels/${CHANNEL_ID}/messages/${saved.messageId}`);
        if (message.author.id !== botId) throw Error('Saved message belongs to another author');
      }
    }
    const countingState = initializeCountingFrom(readJSON(statePath));
    if (!preview) saveState(countingState);
    do {
      const started = Date.now();
      try {
        const response = await fetch(`${clashProxyOrigin(workspace)}/v1/clans/${encodeURIComponent(CLAN_TAG)}`, { signal: AbortSignal.timeout(15_000) });
        if (!response.ok) throw Error(`Clan roster fetch failed (${response.status})`);
        const now = new Date();
        const rows = await loadLeaderboard(pool, await response.json(), countingState.countingFrom, now);
        const payload = messagePayload(rows, countingState.countingFrom, now);
        if (preview) { console.log(JSON.stringify({ rows, payload }, null, 2)); return; }
        const state = await publishMessage(api, readJSON(statePath), payload, saveState, botId, Date.now());
        console.log(JSON.stringify({ at: state.updatedAt, messageId: state.messageId, players: rows.length, top: rows[0] ? { name: rows[0].name, loot: rows[0].loot, attacks: rows[0].attacks } : null }));
      } catch (error) {
        if (preview || error instanceof DiscordError && [401, 403, 404].includes(error.status) || error.message.startsWith('Uncertain initial send')) throw error;
        // Keep the last successful message if the proxy/database is temporarily unavailable.
        console.error(`${new Date().toISOString()} ${error.message}`);
      }
      if (!stop) await sleep(Math.max(0, INTERVAL_MS - (Date.now() - started)), undefined, { signal: abort.signal }).catch(error => { if (error.name !== 'AbortError') throw error; });
    } while (!stop);
  } finally {
    await pool.end();
    if (locked) unlinkSync(lockPath);
  }
}

async function main() {
  mkdirSync(stateDir, { recursive: true, mode: 0o700 });
  const action = process.argv[2] ?? 'preview';
  if (action === 'preview' || action === 'run') return run(action === 'preview');
  const lock = readJSON(lockPath);
  if (action === 'status') {
    console.log(JSON.stringify({ running: Boolean(lock && alive(lock.pid)), ...lock, ...readJSON(statePath), logPath }, null, 2));
  } else if (action === 'start') {
    if (lock && alive(lock.pid)) throw Error('Leaderboard is already running');
    const fd = openSync(logPath, 'a', 0o600);
    const child = spawn(process.execPath, [scriptPath, 'run'], { detached: true, env: inheritedEnvironment(), stdio: ['ignore', fd, fd] });
    child.unref(); closeSync(fd);
    console.log(JSON.stringify({ pid: child.pid, logPath }));
  } else if (action === 'stop') {
    if (lock && alive(lock.pid)) {
      const command = execFileSync('ps', ['-p', String(lock.pid), '-o', 'command='], { encoding: 'utf8' }).trim();
      if (command !== `${process.execPath} ${scriptPath} run`) throw Error('Saved PID belongs to an unexpected process');
      process.kill(lock.pid, 'SIGTERM');
    }
    console.log('Stop requested');
  } else throw Error('Use preview, start, run, status, or stop');
}
if (process.argv[1] && scriptPath === resolve(process.argv[1])) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
