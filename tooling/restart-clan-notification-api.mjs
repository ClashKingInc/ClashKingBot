// Rebuild/restart the existing local API with its intended workspace launcher.
import { execFileSync, spawn } from 'node:child_process';
import { openSync, closeSync } from 'node:fs';
import { loadWorkspace } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import { serviceDefinition } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/services.mjs';
const workspace = loadWorkspace('/Users/matthewanderson/ClashKing');
if (workspace.env.TIMESCALE_HOST !== '127.0.0.1' || workspace.env.TIMESCALE_PORT !== '54330') throw Error('Expected the local development database');
const definition = serviceDefinition(workspace, 'api');
const suffix = `${definition.args[0]}`;
const matches = execFileSync('ps', ['-axo', 'pid=,command='], { encoding: 'utf8' }).split('\n')
  .filter(line => line.trim().endsWith(`node ${suffix}`));
if (matches.length !== 1) throw Error('Expected exactly one existing local API launcher');
const pid = Number(matches[0].trim().split(/\s+/)[0]);
process.kill(pid, 'SIGTERM');
const alive = () => { try { process.kill(pid, 0); return true; } catch { return false; } };
const deadline = Date.now() + 15000;
while (alive() && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 100));
if (alive()) throw Error('The old API launcher did not stop');
const log = `/private/tmp/clashking-local-bot-logs/api-clan-notifications-${Date.now()}.log`;
const fd = openSync(log, 'a', 0o600);
const child = spawn(definition.command, definition.args, { cwd: definition.cwd, env: definition.env, detached: true, stdio: ['ignore', fd, fd] });
child.unref(); closeSync(fd);
console.log(JSON.stringify({ pid: child.pid, log }));
