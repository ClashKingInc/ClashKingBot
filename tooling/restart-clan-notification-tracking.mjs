// Restart only the local workers affected by explicit clan notification follows.
// Credentials come from the configured local workspace and its private push file.
import { readFileSync, writeFileSync, openSync, closeSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { loadWorkspace, inheritedEnvironment } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import { localNotificationLab } from '/Users/matthewanderson/PycharmProjects/clashking_api/scripts/local-notification-lab.mjs';
import { localProxyOrigin } from './local-log-config.mjs';

const workspace = loadWorkspace('/Users/matthewanderson/ClashKing');
const directory = '/private/tmp/clashking-local-bot-logs';
const manifestPath = join(directory, 'processes.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
const config = JSON.parse(readFileSync(join(directory, 'config.json'), 'utf8'));
if (workspace.env.DISCORD_CLIENT_ID !== '808566437199216691' ||
    workspace.env.TIMESCALE_HOST !== '127.0.0.1' || workspace.env.TIMESCALE_PORT !== '54330' ||
    manifest.guild !== '1317858645349765150' || manifest.stream !== config.events.stream) {
  throw Error('Expected the existing local Beta tracking workspace');
}
const scripts = process.argv.includes('--discord-only')
  ? ['discord-delivery']
  : process.argv.includes('--proxy-clients')
    ? ['availability', 'trackedclans', 'trackedplayers', 'capital', 'reminders', 'notifications']
    : ['trackedclans', 'capital', 'reminders', 'notifications'];
const commands = execFileSync('ps', ['-axo', 'pid=,command='], { encoding: 'utf8' }).split('\n');
const targets = scripts.map(script => {
  const matches = commands.filter(line => new RegExp(`^\\s*\\d+\\s+/(?:private/)?tmp/clashking-local-bot-logs/tracking[^ ]* --script ${script}$`).test(line));
  if (matches.length > 1) throw Error(`Expected at most one local ${script} worker`);
  return { script, pid: matches.length ? Number(matches[0].trim().split(/\s+/)[0]) : null };
});
const push = localNotificationLab(true, workspace.config.localPushCredentialsFile).bindings;
if (!push.MOBILE_PUSH_FCM_SERVICE_ACCOUNT_JSON) throw Error('Configure the existing local push credential file first');
const keys = ['TIMESCALE_HOST', 'TIMESCALE_PORT', 'TIMESCALE_DATABASE', 'TIMESCALE_USERNAME', 'TIMESCALE_PASSWORD', 'TIMESCALE_SSLMODE', 'VALKEY_HOST', 'VALKEY_PORT', 'VALKEY_PASSWORD', 'DISCORD_BOT_TOKEN', 'DATA_ENCRYPTION_KEY'];
const env = { ...inheritedEnvironment(), ...Object.fromEntries(keys.map(key => [key, workspace.env[key] ?? ''])),
  ...push, CLASHKING_PROXY_INTERNAL_ORIGIN: localProxyOrigin(workspace),
  DISCORD_GUILD_ALLOWLIST: manifest.guild, DISCORD_MESSAGE_CREATE_ENABLED: 'false' };
const run = Date.now();
const binary = join(directory, `tracking-clan-notifications-${run}`);
execFileSync('go', ['build', '-o', binary, '.'], { cwd: workspace.config.repositories.tracking, stdio: 'inherit' });
const alive = pid => { try { process.kill(pid, 0); return true; } catch (error) { return error.code === 'EPERM'; } };
for (const target of targets) if (target.pid !== null) process.kill(target.pid, 'SIGTERM');
const deadline = Date.now() + 15000;
while (targets.some(target => target.pid !== null && alive(target.pid)) && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 100));
if (targets.some(target => target.pid !== null && alive(target.pid))) throw Error('A local worker did not stop; no replacements started');
const replacements = scripts.map(script => {
  const log = join(directory, `${script}-clan-notifications-${run}.log`);
  const fd = openSync(log, 'a', 0o600);
  const child = spawn(binary, ['--script', script], { cwd: directory, env, detached: true, stdio: ['ignore', fd, fd] });
  child.unref(); closeSync(fd);
  return { script, pid: child.pid, log };
});
writeFileSync(manifestPath, JSON.stringify({ ...manifest, restartedAt: new Date().toISOString(), processes: [
  ...manifest.processes.filter(entry => !scripts.includes(entry.script)), ...replacements,
] }, null, 2), { mode: 0o600 });
console.log(JSON.stringify({ stream: manifest.stream, restarted: replacements }, null, 2));
