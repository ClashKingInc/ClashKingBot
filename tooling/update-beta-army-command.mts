// Update only /army on the explicitly approved Beta application. Never replace
// the global command collection or infer a target from the token alone.
import {commandDefinitions} from '../worker/src/commands/registry.ts';
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
const {env}=loadWorkspace('/Users/matthewanderson/ClashKing');
const app='808566437199216691';
if(env.DISCORD_CLIENT_ID!==app)throw Error('Only the approved Beta application is allowed');
const headers={Authorization:`Bot ${env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
const base=`https://discord.com/api/v10/applications/${app}/commands`;
async function list(){const response=await fetch(base,{headers});if(!response.ok)throw Error(`Command listing HTTP ${response.status}`);return await response.json() as Array<{id:string;name:string;options?:unknown[]}>;}
const before=await list(),army=before.find(command=>command.name==='army');
if(!army)throw Error('Existing Beta army command not found');
const definition=commandDefinitions.find(command=>command.name==='army');
const response=await fetch(`${base}/${army.id}`,{method:'PATCH',headers,body:JSON.stringify(definition)});
if(!response.ok)throw Error(`Beta army update HTTP ${response.status}`);
const after=await list(),updated=after.find(command=>command.name==='army');
if(before.filter(c=>c.name!=='army').map(c=>c.id).sort().join()!==after.filter(c=>c.name!=='army').map(c=>c.id).sort().join())throw Error('Unexpected unrelated command changes');
console.log(JSON.stringify({application:app,updated:updated?.name,options:updated?.options,otherCommandsPreserved:after.length-1}));
