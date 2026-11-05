// Patch only the existing Beta /player definition after local verification.
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import {playerCommand} from '../worker/src/commands/player';
async function main(){
 const workspace=loadWorkspace('/Users/matthewanderson/ClashKing'),app=workspace.env.DISCORD_CLIENT_ID;
 if(app!=='808566437199216691')throw Error('Only the Beta bot is allowed');
 const base=`https://discord.com/api/v10/applications/${app}/commands`,headers={Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
 const response=await fetch(base,{headers});if(!response.ok)throw Error(`Command lookup HTTP ${response.status}`);
 const existing=(await response.json()).find((command:{name:string})=>command.name==='player');
 if(!existing)throw Error('Existing player command not found');
 const result=await fetch(`${base}/${existing.id}`,{method:'PATCH',headers,body:JSON.stringify(playerCommand.definition)});
 if(!result.ok)throw Error(`Command update HTTP ${result.status}`);
 const updated=await result.json();console.log(JSON.stringify({application:app,command:updated.name,subcommands:updated.options.map((item:{name:string})=>item.name)}));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
