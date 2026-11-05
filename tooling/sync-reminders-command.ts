// Update only the manual reminder definition on the local workspace's Beta bot.
import { loadWorkspace } from '/Users/matthewanderson/GolandProjects/clashking_schemas/cli/src/workspace.mjs';
import { remindersCommand } from '../worker/src/commands/reminders';
async function main(){
const workspace=loadWorkspace('/Users/matthewanderson/ClashKing');
const app=workspace.env.DISCORD_CLIENT_ID;
if(app!=='808566437199216691')throw Error('Only the Beta bot is allowed');
if(!process.argv.includes('--apply')){
 console.log(JSON.stringify({command:remindersCommand.definition,apply:false}));
}else{
 const url=`https://discord.com/api/v10/applications/${app}/commands`;
 const headers={Authorization:`Bot ${workspace.env.DISCORD_BOT_TOKEN}`,'Content-Type':'application/json'};
 const response=await fetch(url,{headers});if(!response.ok)throw Error(`Command lookup HTTP ${response.status}`);
 const commands=await response.json() as Array<{id:string;name:string}>;
 const existing=commands.find(command=>command.name==='reminders');
 const saved=await fetch(existing?`${url}/${existing.id}`:url,{method:existing?'PATCH':'POST',headers,body:JSON.stringify(remindersCommand.definition)});
 if(!saved.ok)throw Error(`Command registration HTTP ${saved.status}`);
 console.log(JSON.stringify({application:app,command:'reminders',registered:true}));
}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
