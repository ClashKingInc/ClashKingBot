import { legacyMessage } from "../discord/components";
import { CommandInputError, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import type { CommandContext } from "./types";
export const memberWarningOptions=[
 {name:"action",description:"View, configure or disable the alert",type:3,required:true,choices:[{name:"View",value:"view"},{name:"Set",value:"set"},{name:"Disable",value:"disable"}]},
 {name:"channel",description:"Text channel for warnings",type:7},
 {name:"below",description:"Alert when the count falls strictly below this",type:4,min_value:1,max_value:50},
 {name:"above",description:"Alert when the count rises strictly above this",type:4,min_value:0,max_value:49},
 {name:"role",description:"Optional role to mention in warnings",type:8},
];
export async function memberWarning(ctx:CommandContext){
 const guild=requireGuildId(ctx),permissions=ctx.interaction.member?.permissions??"0";
 if(!/^\d+$/u.test(permissions)||(BigInt(permissions)&40n)===0n)throw new CommandInputError("Manage Server is required for member warnings.");
 const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale),action=stringOption(ctx,"action"),path=`/v2/server/${guild}/clan/${encodeURIComponent(tag)}/member-warning`;
 if(action==="disable"){await ctx.services.api.delete(path);return legacyMessage({content:`Member-count warnings disabled for ${tag}.`},{ephemeral:true});}
 type Settings={channelId:string;below:number|null;above:number|null;roleId:string|null};
 let result:{settings:Settings|null};
 if(action==="set"){
  const channel=stringOption(ctx,"channel"),below=ctx.options.get("below")?.value??null,above=ctx.options.get("above")?.value??null;
  if(!channel||(below===null&&above===null))throw new CommandInputError("Choose a channel and at least one threshold. Setting replaces the previous configuration.");
  result=await ctx.services.api.put(path,{channelId:channel,below,above,roleId:stringOption(ctx,"role")??null});
 }else if(action==="view")result=await ctx.services.api.get(path);
 else throw new CommandInputError("Choose View, Set or Disable.");
 const s=result.settings;
 return legacyMessage({allowed_mentions:{parse:[]},content:s?`${action==="set"?"Saved":"Current"} warnings for ${tag}\nChannel: <#${s.channelId}>\n${s.below===null?"":`Below ${s.below} members\n`}${s.above===null?"":`Above ${s.above} members\n`}Mention: ${s.roleId?`<@&${s.roleId}>`:"None"}\nAlerts fire only when the count crosses a threshold.`:`No member-count warnings configured for ${tag}.`},{ephemeral:true});
}
