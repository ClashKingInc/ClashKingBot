import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, requireGuildId } from "./command-utils";
import { playerCommand } from "./player";
import { refreshCommand } from "./refresh";
import { serverEmbedColor } from "./embed-color";
import type { Command, CommandContext } from "./types";
const actions={link:"Link account",help:"Link help",refresh:"Refresh roles",todo:"My to-do",rosters:"My rosters"};
interface SavedEmbed{name:string;data:{flags?:number;content?:string;embeds?:unknown[]}}
function manager(ctx:CommandContext){const p=ctx.interaction.member?.permissions??"0";if(!/^\d+$/u.test(p)||(BigInt(p)&40n)===0n)throw new CommandInputError("Manage Server is required to post a button panel.");}
export const buttonsCommand:Command={
 deferred:true,ephemeral:true,
 definition:{name:"buttons",description:"Post a member action panel",type:1,contexts:[0],integration_types:[0],default_member_permissions:"32",options:[
  {name:"channel",type:7,description:"Text channel (default current)"},{name:"embed",type:3,description:"Saved server embed to use",autocomplete:true},
  {name:"text",type:3,description:"Panel text (overrides saved text)",max_length:2000},
  {name:"color",type:3,description:"Button color",choices:[{name:"Grey",value:"2"},{name:"Blue",value:"1"},{name:"Green",value:"3"},{name:"Red",value:"4"}]},
  ...Object.entries(actions).map(([name,label])=>({name,type:5,description:`Include ${label} (default ${name==='help'?'off':'on'})`})),
 ]},
 async autocomplete(ctx){manager(ctx);const q=String(ctx.interaction.data?.options?.find(o=>o.focused)?.value??"").toLowerCase();const {items}=await ctx.services.api.get<{items:SavedEmbed[]}>(`/v2/server/${requireGuildId(ctx)}/embeds`);return items.filter(item=>item.name.toLowerCase().includes(q)).slice(0,25).map(item=>({name:item.name.slice(0,100),value:item.name}));},
 async execute(ctx){
  manager(ctx);const guild=requireGuildId(ctx),channel=String(ctx.options.get('channel')?.value??ctx.interaction.channel_id??'');
  if(!/^\d{15,20}$/u.test(channel))throw new CommandInputError("Choose a text channel.");
  const destination=await ctx.services.discordRest.getChannel(channel);
  if(destination.guild_id!==guild||![0,5].includes(destination.type))throw new CommandInputError("Choose a text channel in this server.");
  const selected=Object.keys(actions).filter(action=>ctx.options.get(action)?.value??action!=='help');
  if(!selected.length)throw new CommandInputError("Enable at least one panel button.");
  const style=Number(ctx.options.get('color')?.value??2);if(![1,2,3,4].includes(style))throw new CommandInputError("Choose a valid button color.");
  let content=String(ctx.options.get('text')?.value??""),embeds:unknown[]|undefined;
  const embed=ctx.options.get('embed')?.value;
  if(embed){const {items}=await ctx.services.api.get<{items:SavedEmbed[]}>(`/v2/server/${guild}/embeds`);const saved=items.find(item=>item.name===embed);if(!saved)throw new CommandInputError("Saved embed not found in this server.");if((Number(saved.data.flags??0)&32768)!==0)throw new CommandInputError("Choose a classic saved embed for this button panel.");embeds=saved.data.embeds;content=content||saved.data.content||"";}
  if(!content&&!embeds?.length)embeds=[{title:"Your ClashKing accounts",description:"Link an account, refresh your roles, or check your tasks and rosters.",color:await serverEmbedColor(ctx)}];
  const payload={content,...(embeds?{embeds}:{}),allowed_mentions:{parse:[]},components:[actionRow(...selected.map(action=>({type:2 as const,style:style as 1|2|3|4,label:actions[action as keyof typeof actions],custom_id:`ck:quick:${guild}:${action}`})))]};
  let message:{id:string};try{message=await ctx.services.discordRest.request(`/channels/${channel}/messages`,{method:'POST',body:JSON.stringify(payload)});}catch{throw new CommandInputError("The panel post could not be confirmed. Check the channel before trying again.");}
  if(!/^\d{15,20}$/u.test(message.id))throw new CommandInputError("The panel post could not be confirmed. Check the channel before trying again.");
  return legacyMessage({content:`[Panel posted](https://discord.com/channels/${guild}/${channel}/${message.id}).`,allowed_mentions:{parse:[]}},{ephemeral:true});
 }
};
export async function quickMemberAction(ctx:CommandContext,action:string){
 // Shared actions must resolve the current clicker, never the panel author.
 if(action==='refresh')return refreshCommand.execute({...ctx,options:new Map()});
 if(action==='todo')return playerCommand.execute({...ctx,options:new Map([['to-do',{name:'to-do',type:1,options:[]}]])});
 if(action!=='rosters')throw new CommandInputError("Unknown member action.");
 const data=await ctx.services.api.get<{truncated:boolean;items:Array<{rosterName:string;playerName:string;playerTag:string;clanName:string|null;groupName:string}>}>(`/v2/bot/servers/${requireGuildId(ctx)}/users/${invokingUserId(ctx)}/rosters`);
 const clean=(value:string)=>value.replace(/[\\`*_~|<>\r\n]/gu,' ');
 let text='',shown=0;for(const row of data.items){const line=`**${clean(row.rosterName)}** · ${clean(row.playerName)} (${row.playerTag}) · ${clean(row.groupName)} · ${clean(row.clanName??'No clan')}`;if(text.length+line.length>3500)break;text+=(text?'\n':'')+line;shown++;}
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:'My rosters',description:text||'None of your visible linked accounts are in this server’s rosters.',footer:{text:`${shown} memberships shown${data.truncated||shown<data.items.length?' · more available':''}`}}]},{ephemeral:true});
}
