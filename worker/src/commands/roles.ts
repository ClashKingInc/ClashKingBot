import { legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, requireGuildId, stringOption } from "./command-utils";
import { subcommand } from "./game-common";
import type { Command } from "./types";
export const rolesCommand:Command={
 deferred:true,ephemeral:true,
 definition:{name:"roles",description:"Configure automatic Discord roles",type:1,contexts:[0],default_member_permissions:"32",options:[{name:"tenure",description:"Set or remove a Discord membership milestone",type:OptionType.Subcommand,options:[
 {name:"mode",description:"Add/update or remove a milestone",type:OptionType.String,required:true,choices:[{name:"Add or update",value:"add"},{name:"Remove",value:"remove"}]},
 {name:"months",description:"Completed calendar months in this server",type:OptionType.Integer,required:true,min_value:1,max_value:1200},
 {name:"role",description:"Role to grant at this milestone",type:OptionType.Role},
 ]}]},
 async execute(context){
  const ctx=subcommand(context),server=requireGuildId(ctx),permission=ctx.interaction.member?.permissions??"0";
  if(!/^\d+$/u.test(permission)||(BigInt(permission)&40n)===0n)throw new CommandInputError("Manage Server is required.");
  const mode=stringOption(ctx,"mode"),months=Number(ctx.options.get("months")?.value),role=stringOption(ctx,"role");
  if(!["add","remove"].includes(mode??"")||!Number.isInteger(months)||months<1||months>1200||mode==="add"&&(!role||!/^\d{15,20}$/u.test(role)||role===server))throw new CommandInputError("Choose a valid milestone and a non-everyone role.");
  const path=`/v2/server/${server}/server-roles`,existing=(await ctx.services.api.get<{roles:Array<{id:string;option:string;role_id:string}>}>(path,{type:"status"})).roles.filter(rule=>rule.option===String(months));
  if(mode==="remove"){
   for(const rule of existing)await ctx.services.api.delete(`${path}/${rule.id}`);
   return legacyMessage({content:existing.length?`Removed the ${months}-month tenure rule. Existing Discord assignments remain unmanaged until another rule applies.`:"No tenure rule exists for that milestone."},{ephemeral:true});
  }
  if(existing.length>1)throw new CommandInputError("Multiple rules use this milestone. Remove that milestone before adding its replacement.");
  if(existing[0])await ctx.services.api.patch(`${path}/${existing[0].id}`,{role_id:role});
  else await ctx.services.api.post(path,{type:"status",option:String(months),role_id:role});
  return legacyMessage({allowed_mentions:{parse:[]},content:`Saved the ${months}-month tenure role: <@&${role}>. The highest earned milestone applies; the bot must be above that role.`},{ephemeral:true});
 },
};
