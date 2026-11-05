// Local-only tracking harness. Uses the real Tracking binary and fresh streams;
// never loads the Tracking repository's .env or production Discord credentials.
import { readFileSync, writeFileSync, mkdirSync, openSync, closeSync, existsSync, renameSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { loadWorkspace, inheritedEnvironment } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import { localProxyOrigin, localTrackingScripts } from './local-log-config.mjs';

const workspace = loadWorkspace('/Users/matthewanderson/ClashKing');
const directory = '/tmp/clashking-local-bot-logs';
const manifestPath = join(directory, 'processes.json');
const action = process.argv[2] ?? 'status';
const live = pid => { try { process.kill(pid, 0); return true; } catch (error) { return error.code === 'EPERM'; } };
const existing = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : undefined;
if (action === 'status') {
  console.log(JSON.stringify(existing ? { ...existing, processes: existing.processes.map(p => ({ ...p, alive: live(p.pid) })) } : { running: false }, null, 2));
} else if (action === 'start') {
  if (existing?.processes.some(p => live(p.pid))) throw Error('This local harness is already running; inspect status first');
  if (workspace.env.DISCORD_CLIENT_ID !== '808566437199216691') throw Error('Expected ClashKing Beta');
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const cfg = JSON.parse(readFileSync(join(workspace.config.repositories.tracking, 'config.json'), 'utf8'));
  const run = Date.now().toString();
  cfg.events.stream = `tracking:bot-log-local:${run}`;
  cfg.events.consumer = `bot-log-local-${run}`;
  cfg.trackedclans.requests_per_second = 1;
  cfg.trackedclans.target_refresh_seconds = 30;
  cfg.trackedclans.snapshot_prefix = `bot-log-local:${run}:clan:`;
  cfg.trackedclans.cwl_state_snapshot = `bot-log-local:${run}:cwl`;
  cfg.trackedplayers.requests_per_second = 2;
  cfg.trackedplayers.target_refresh_seconds = 30;
  cfg.capital.requests_per_second = 1;
  cfg.capital.target_refresh_seconds = 30;
  cfg.capital.snapshot_prefix = `bot-log-local:${run}:capital:`;
  cfg.discord_gateway.message_create_enabled = false;
  writeFileSync(join(directory, 'config.json'), JSON.stringify(cfg, null, 2), { mode: 0o600 });
  const binary = join(directory, 'tracking');
  execFileSync('go', ['build', '-o', binary, '.'], { cwd: workspace.config.repositories.tracking, stdio: 'inherit' });
  const keys = ['TIMESCALE_HOST','TIMESCALE_PORT','TIMESCALE_DATABASE','TIMESCALE_USERNAME','TIMESCALE_PASSWORD','TIMESCALE_SSLMODE','VALKEY_HOST','VALKEY_PORT','VALKEY_PASSWORD','DISCORD_BOT_TOKEN'];
  const env = { ...inheritedEnvironment(), ...Object.fromEntries(keys.map(key => [key, workspace.env[key] ?? ''])),
    CLASHKING_PROXY_INTERNAL_ORIGIN: localProxyOrigin(workspace),
    DISCORD_GUILD_ALLOWLIST: '1317858645349765150', DISCORD_MESSAGE_CREATE_ENABLED: 'false',
  };
  // Restore the approved Beta giveaway test alongside the local log trackers.
  // No gateway duplicate, mobile sends, scheduled reminders, global discovery
  // or Reddit collection. Those require their own reviewed test slice.
  const processes = [];
  for (const script of localTrackingScripts) {
    const log = join(directory, `${script}-${run}.log`), fd = openSync(log, 'a', 0o600);
    const child = spawn(binary, ['--script', script], { cwd: directory, env, detached: true, stdio: ['ignore', fd, fd] });
    child.unref(); closeSync(fd);
    processes.push({ script, pid: child.pid, log });
  }
  const manifest = { startedAt: new Date().toISOString(), stream: cfg.events.stream, guild: '1317858645349765150', processes };
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), { mode: 0o600 });
  console.log(JSON.stringify(manifest, null, 2));
} else if (action === 'restart') {
  // Preserve the stream and snapshots so failed real events can recover.
  if (!existing || workspace.env.DISCORD_CLIENT_ID !== '808566437199216691') throw Error('Expected an existing local Beta run');
  const binary = join(directory, 'tracking');
  for (const processInfo of existing.processes) {
    if (!live(processInfo.pid)) continue;
    const command = execFileSync('ps', ['-p', String(processInfo.pid), '-o', 'comm='], { encoding: 'utf8' }).trim();
    if (command !== binary) throw Error(`Refusing to stop unexpected process ${processInfo.pid}`);
  }
  execFileSync('go', ['build', '-o', `${binary}.next`, '.'], { cwd: workspace.config.repositories.tracking, stdio: 'inherit' });
  for (const p of existing.processes) if (live(p.pid)) process.kill(p.pid, 'SIGTERM');
  const deadline = Date.now() + 15000;
  while (existing.processes.some(p => live(p.pid)) && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 100));
  if (existing.processes.some(p => live(p.pid))) throw Error('A local tracker did not stop; no replacement started');
  renameSync(`${binary}.next`, binary);
  const keys = ['TIMESCALE_HOST','TIMESCALE_PORT','TIMESCALE_DATABASE','TIMESCALE_USERNAME','TIMESCALE_PASSWORD','TIMESCALE_SSLMODE','VALKEY_HOST','VALKEY_PORT','VALKEY_PASSWORD','DISCORD_BOT_TOKEN'];
  const env = { ...inheritedEnvironment(), ...Object.fromEntries(keys.map(key => [key, workspace.env[key] ?? ''])),
    CLASHKING_PROXY_INTERNAL_ORIGIN: localProxyOrigin(workspace),
    DISCORD_GUILD_ALLOWLIST: existing.guild, DISCORD_MESSAGE_CREATE_ENABLED: 'false',
  };
  const run = Date.now();
  const processes = localTrackingScripts.map(script => {
    const log = join(directory, `${script}-${run}.log`), fd = openSync(log, 'a', 0o600);
    const child = spawn(binary, ['--script', script], { cwd: directory, env, detached: true, stdio: ['ignore', fd, fd] });
    child.unref(); closeSync(fd);
    return { script, pid: child.pid, log };
  });
  const manifest = { ...existing, restartedAt: new Date().toISOString(), processes };
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), { mode: 0o600 });
  console.log(JSON.stringify(manifest, null, 2));
} else {
  throw Error('Use start, restart or status. Restart preserves the existing stream and snapshots.');
}
