// Disposable domain fixtures for the authenticated local Dashboard browser pass.
// Browser authentication remains the normal approved Discord OAuth session.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { loadLocalApiSecrets } from '/Users/matthewanderson/PycharmProjects/clashking_api/scripts/local-api-keychain.mjs';
const require = createRequire('/Users/matthewanderson/PycharmProjects/clashking_api/workers/api/package.json');
const pg = require('pg');
const [mode, file] = process.argv.slice(2), fixture = JSON.parse(readFileSync(file, 'utf8'));
if (!fixture.email.endsWith('@competitive-qa.clashking.invalid')) throw Error('Expected owned synthetic identity');
const serverId = '1317858645349765150', opponentTag = '#QYLL0P2Q';
const teamNames = ['QA · Browser Duo · 2026-10-17', 'QA · Browser Ten · 2026-10-17', 'QA · Browser Opponent · 2026-10-17'];
const tournamentName = 'QA · Browser Cup · 2026-10-17';
const db = new pg.Client({ connectionString: 'postgres://clashking_local:clashking_local@127.0.0.1:54330/clashking_dev' });
await db.connect();
try {
  if ((await db.query('SELECT name FROM servers WHERE id=$1', [serverId])).rows[0]?.name !== 'ClashKing Dev') throw Error('Expected existing local development server');
  if (mode === 'cleanup') {
    const teamIds = (await db.query('SELECT id FROM competitive_teams WHERE server_id=$1 AND internal_name=ANY($2::text[])', [serverId, teamNames])).rows.map(r => r.id);
    const eventIds = (await db.query('SELECT id FROM competitive_tournaments WHERE server_id=$1 AND name=$2', [serverId, tournamentName])).rows.map(r => r.id);
    const matchIds = (await db.query('SELECT id FROM competitive_matches WHERE tournament_id=ANY($1::uuid[])', [eventIds])).rows.map(r => r.id);
    await db.query('BEGIN');
    await db.query('DELETE FROM competitive_matches WHERE id=ANY($1::uuid[])', [matchIds]);
    await db.query('DELETE FROM competitive_participants WHERE tournament_id=ANY($1::uuid[])', [eventIds]);
    await db.query('DELETE FROM competitive_tournaments WHERE id=ANY($1::uuid[])', [eventIds]);
    await db.query('DELETE FROM competitive_team_members WHERE team_id=ANY($1::uuid[])', [teamIds]);
    await db.query('DELETE FROM competitive_teams WHERE id=ANY($1::uuid[])', [teamIds]);
    await db.query('DELETE FROM competitive_audit WHERE server_id=$1 AND entity_id=ANY($2::text[])', [serverId, [...teamIds, ...eventIds, ...matchIds]]);
    if (fixture.dashboard?.opponentCreated) {
      await db.query('DELETE FROM server_clan_verifications WHERE server_id=$1 AND clan_tag=$2', [serverId, opponentTag]);
      await db.query('DELETE FROM server_clans WHERE server_id=$1 AND tag=$2', [serverId, opponentTag]);
      await db.query("DELETE FROM basic_clan WHERE tag=$1 AND name='Northstar · Local QA'", [opponentTag]);
    }
    await db.query('COMMIT');
    console.log(JSON.stringify({ cleanedTeams: teamIds.length, cleanedEvents: eventIds.length, cleanedMatches: matchIds.length, preservedExistingServer: true }));
  } else {
    const keys = loadLocalApiSecrets();
    async function request(path, data, token = keys.API_BOT_TOKEN) {
      const response = await fetch('http://127.0.0.1:8787' + path, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      const result = await response.json();
      if (!response.ok) throw Error(`${path}: ${response.status} ${JSON.stringify(result)}`);
      return result;
    }
    const session = await request('/v2/auth/email', { email: fixture.email, password: fixture.password, device_id: 'dashboard-visual-local', device_name: 'Local browser QA' });
    const base = `/v2/competitive/servers/${serverId}`;
    if (mode === 'prepare') {
      if (fixture.dashboard) throw Error('Fixtures already prepared');
      const home = (await db.query('SELECT id FROM competitive_teams WHERE server_id=$1 AND internal_name=$2', [serverId, teamNames[0]])).rows;
      if (home.length !== 1) throw Error('Create the one disposable duo in the real Dashboard first');
      if ((await db.query('SELECT 1 FROM basic_clan WHERE tag=$1', [opponentTag])).rowCount) throw Error('Opponent fixture already exists');
      fixture.dashboard = { serverId, homeTeamId: home[0].id, opponentCreated: true };
      writeFileSync(file, JSON.stringify(fixture), { mode: 0o600 });
      // Only the nonexistent QA opponent gets fixture verification. The real
      // clan's existing verification and Discord authorization are untouched.
      await db.query("INSERT INTO basic_clan(tag,name,public_war_log,war_wins,member_count,badge_token,troops_donated,troops_received) VALUES($1,'Northstar · Local QA',true,0,2,'local',0,0)", [opponentTag]);
      await db.query('INSERT INTO server_clans(tag,server_id) VALUES($1,$2)', [opponentTag, serverId]);
      await db.query("INSERT INTO server_clan_verifications(server_id,clan_tag,challenge_id,marker,marker_index,requested_by,state,check_after,next_check_at,expires_at,verified_at) VALUES($1,$2,$3,'appleck',0,$4,'verified',now()+interval '2 minutes',now(),now()+interval '1 day',now())", [serverId, opponentTag, randomUUID(), fixture.userId]);
      const away = await request(base + '/teams', { clanTag: opponentTag, internalName: teamNames[2], size: 2 });
      fixture.dashboard.awayTeamId = away.id;
      writeFileSync(file, JSON.stringify(fixture), { mode: 0o600 });
      for (const [i, teamId] of [home[0].id, away.id].entries()) {
        for (const playerTag of fixture.tags.slice(i * 2, i * 2 + 2)) {
          if (!(await db.query('SELECT 1 FROM competitive_team_members WHERE team_id=$1 AND player_tag=$2 AND left_at IS NULL', [teamId, playerTag])).rowCount) await request(base + `/teams/${teamId}/members`, { playerTag });
          await request(`/v2/competitive/teams/${teamId}/join`, { playerTag }, session.access_token);
        }
      }
      console.log('Prepared two accepted synthetic rosters; no registration, match, score or external Discord message created');
    } else if (mode === 'check-in') {
      const events = (await db.query('SELECT id FROM competitive_tournaments WHERE server_id=$1 AND name=$2', [serverId, tournamentName])).rows;
      if (events.length !== 1) throw Error('Expected exactly one UI-created QA event');
      fixture.dashboard.tournamentId = events[0].id;
      writeFileSync(file, JSON.stringify(fixture), { mode: 0o600 });
      for (const teamId of [fixture.dashboard.homeTeamId, fixture.dashboard.awayTeamId]) await request(`/v2/competitive/tournaments/${events[0].id}/check-in`, { teamId }, session.access_token);
      console.log('Both verified synthetic rosters checked in through the real local member API');
    } else throw Error('Expected prepare, check-in or cleanup');
  }
} finally { await db.end(); }
