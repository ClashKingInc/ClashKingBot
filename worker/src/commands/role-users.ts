import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import { escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { Command } from "./types";
const size=20;
const clean=(value:string)=>escapeMarkdown(value.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"").slice(0,65));
export const roleUsersCommand:Command={
 deferred:true,
 definition:{name:"role-users",description:"List members who have a Discord role",type:1,contexts:[0],options:[{name:"role",description:"Role to list",type:OptionType.Role,required:true}]},
 async execute(ctx){
  const server=requireGuildId(ctx),role=stringOption(ctx,"role")??"",page=Number(ctx.options.get("__page")?.value??0);
  if(!/^\d{15,20}$/u.test(role)||!Number.isSafeInteger(page)||page<0||page>100000)throw new CommandInputError("Choose a valid role.");
  const get=(offset:number)=>ctx.services.api.get<{role:{id:string;name:string};total:number;offset:number;items:Array<{id:string;name:string}>}>(`/v2/bot/servers/${server}/roles/${role}/members`,{actorId:invokingUserId(ctx),offset,limit:size});
  let result=await get(page*size);
  const last=Math.max(0,Math.ceil(result.total/size)-1),current=Math.min(page,last);
  if(current!==page)result=await get(current*size);
  const button=(label:string,target:number)=>({type:2 as const,style:2 as const,label,custom_id:`ck:page:ru:${invokingUserId(ctx)}:${role}:${target}`});
  const controls=[button("Refresh",current)];
  if(current>0)controls.push(button("←",current-1));
  if(current<last)controls.push(button("→",current+1));
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:`${clean(result.role.name)} · ${result.total} members`,color:await serverEmbedColor(ctx),description:result.items.map(member=>`${clean(member.name)} · <@${member.id}>`).join("\n")||"No members have this role.",footer:{text:`Page ${current+1}/${last+1}`}}],components:[actionRow(...controls)]});
 },
};
