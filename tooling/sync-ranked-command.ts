// Update only the existing Beta /ranked definition. Never bulk-overwrite commands.
import { loadWorkspace } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import { rankedCommand } from '../worker/src/commands/ranked';
async function main(){
const workspace=loadWorkspace('/Users/matthewanderson/ClashKing');
const app=workspace.env.DISCORD_CLIENT_ID;
if(app!=='808566437199216691')throw Error('Only the Beta bot is allowed');
const base=`https://discord.com/api/v10/applications/${app}/commands`;
const headers={Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
const response=await fetch(base,{headers});if(!response.ok)throw Error(`Command lookup HTTP ${response.status}`);
const current=(await response.json()).find((command:{name:string})=>command.name==='ranked');
if(!current)throw Error('Existing Beta /ranked command not found');
const result=await fetch(`${base}/${current.id}`,{method:'PATCH',headers,body:JSON.stringify(rankedCommand.definition)});
if(!result.ok)throw Error(`Command update HTTP ${result.status}`);
const updated=await result.json();
console.log(JSON.stringify({application:app,command:updated.name,subcommands:updated.options.map((option:{name:string})=>option.name)}));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
