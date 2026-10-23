// Local review content only. No remote origin, Discord action or production data.
import { loadLocalApiSecrets } from '/Users/matthewanderson/PycharmProjects/clashking_api/scripts/local-api-keychain.mjs';
import { createRequire } from 'node:module';
const require = createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/package.json');
const { Client } = require('pg');
const db = new Client({ connectionString: 'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev' });
const serverId = '1317858645349765150';
const base = `http://127.0.0.1:8787/v2/competitive/servers/${serverId}`;
await db.connect();
try {
  if ((await db.query('SELECT name FROM servers WHERE id=$1', [serverId])).rows[0]?.name !== 'ClashKing Dev') throw Error('Expected local development server');
  const { API_BOT_TOKEN } = loadLocalApiSecrets();
  const request = async (path, method, body) => {
    const response = await fetch(base + path, { method, headers: { authorization: `Bearer ${API_BOT_TOKEN}`, 'content-type': 'application/json' }, body: JSON.stringify(body) });
    if (!response.ok) throw Error(`Local preview request failed: ${response.status}`);
    return response.json();
  };
  for (const [name, format, size, days, length, description] of [
    ['ClashKing Open', 'single_elimination', 5, 3, 2, 'Five players. One clan. A weekend of head-to-head wars.'],
    ['Weekend Duos', 'double_elimination', 2, 5, 2, 'Bring your duo. Double elimination keeps every comeback alive.'],
    ['Arena League', 'elo', 10, 7, 7, 'A seven-day ladder for ten-player clan lineups.'],
  ]) {
    const existing = await db.query('SELECT id FROM competitive_tournaments WHERE server_id=$1 AND name=$2', [serverId, name]);
    if (existing.rowCount) continue;
    const startsAt = new Date(Date.now() + days * 86400000).toISOString();
    const event = await request('/tournaments', 'POST', { name, format, teamSize: size, startsAt, endsAt: new Date(Date.parse(startsAt) + length * 86400000).toISOString(), rules: { description, minTownHall: 16, maxTownHall: 18, maxRosterSize: size, visibility: 'public' } });
    await request(`/tournaments/${event.id}`, 'PUT', { status: 'registration' });
    console.log(JSON.stringify({ localPreviewEvent: name, id: event.id }));
  }
} finally { await db.end(); }
