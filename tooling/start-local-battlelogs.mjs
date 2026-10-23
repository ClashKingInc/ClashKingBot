// Start only battlelogs against the existing local Beta stack.
import { readFileSync, writeFileSync, mkdirSync, openSync, closeSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { loadWorkspace, inheritedEnvironment } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import { localProxyOrigin } from './local-log-config.mjs';

const workspace = loadWorkspace('/Users/matthewanderson/ClashKing');
const root = '/tmp/clashking-local-bot-logs';
const directory = join(root, 'battlelogs');
const manifestPath = join(root, 'processes.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
if (workspace.env.DISCORD_CLIENT_ID !== '808566437199216691' || workspace.env.TIMESCALE_PORT !== '54330' || manifest.guild !== '1317858645349765150') {
  throw Error('Expected the existing local Beta workspace');
}
const commands = execFileSync('ps', ['-axo', 'command='], { encoding: 'utf8' }).split('\n');
if (commands.some(command => /^\/(?:private\/)?tmp\/clashking-local-bot-logs\/\S+ --script battlelogs$/.test(command.trim()))) {
  throw Error('Local battlelogs is already running');
}
const run = manifest.stream.match(/^tracking:bot-log-local:(\d+)$/)?.[1];
if (!run) throw Error('Expected the existing local tracking stream');
const config = JSON.parse(readFileSync(join(workspace.config.repositories.tracking, 'config.json'), 'utf8'));
config.events.stream = manifest.stream;
config.events.consumer = `battlelogs-local-${run}`;
config.trackedclans.snapshot_prefix = `bot-log-local:${run}:clan:`;
config.battlelogs.requests_per_second = 25;
config.battlelogs.priority_requests_per_second = 0;
config.stats.timescale_flush_seconds = 10;
mkdirSync(directory, { recursive: true, mode: 0o700 });
writeFileSync(join(directory, 'config.json'), JSON.stringify(config, null, 2), { mode: 0o600 });
const binary = join(root, 'tracking-battlelogs');
execFileSync('go', ['build', '-o', binary, '.'], { cwd: workspace.config.repositories.tracking, stdio: 'inherit' });
const keys = ['TIMESCALE_HOST', 'TIMESCALE_PORT', 'TIMESCALE_DATABASE', 'TIMESCALE_USERNAME', 'TIMESCALE_PASSWORD', 'TIMESCALE_SSLMODE', 'VALKEY_HOST', 'VALKEY_PORT', 'VALKEY_PASSWORD'];
const env = { ...inheritedEnvironment(), ...Object.fromEntries(keys.map(key => [key, workspace.env[key] ?? ''])),
  CLASHKING_PROXY_INTERNAL_ORIGIN: localProxyOrigin(workspace), DISCORD_GUILD_ALLOWLIST: manifest.guild };
const log = join(directory, `battlelogs-${Date.now()}.log`);
const fd = openSync(log, 'a', 0o600);
const child = spawn(binary, ['--script', 'battlelogs'], { cwd: directory, env, detached: true, stdio: ['ignore', fd, fd] });
child.unref(); closeSync(fd);
const entry = { script: 'battlelogs', pid: child.pid, log };
writeFileSync(manifestPath, JSON.stringify({ ...manifest, processes: [...manifest.processes.filter(p => p.script !== 'battlelogs'), entry] }, null, 2), { mode: 0o600 });
console.log(JSON.stringify(entry));
