// Register only /clan on the explicitly selected local Beta application.
import {loadWorkspace} from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import {clanCommand} from '../worker/src/commands/clan';
async function main(){
 const workspace=loadWorkspace('/Users/matthewanderson/ClashKing'),app=workspace.env.DISCORD_CLIENT_ID;
 if(app!=='808566437199216691')throw Error('Only the Beta bot is allowed');
 if(!process.argv.includes('--apply')){console.log(JSON.stringify({command:'clan',subcommands:clanCommand.definition.options?.map(item=>item.name),apply:false}));return;}
 const base=`https://discord.com/api/v10/applications/${app}/commands`,headers={Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
 const response=await fetch(base,{headers});if(!response.ok)throw Error(`Command lookup HTTP ${response.status}`);
 const existing=(await response.json()).find((command:{name:string})=>command.name==='clan');
 const result=await fetch(existing?`${base}/${existing.id}`:base,{method:existing?'PATCH':'POST',headers,body:JSON.stringify(clanCommand.definition)});
 if(!result.ok)throw Error(`Command registration HTTP ${result.status}`);
 const updated=await result.json();console.log(JSON.stringify({application:app,command:updated.name,subcommands:updated.options.map((item:{name:string})=>item.name)}));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
