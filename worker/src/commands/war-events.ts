import { legacyMessage } from "../discord/components";
import { CommandInputError, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import type { CommandContext } from "./types";
export const warEventsOptions=[{name:"action",description:"View, enable or disable automatic Discord events",type:3,required:true,choices:[{name:"View",value:"view"},{name:"Enable",value:"enable"},{name:"Disable",value:"disable"}]}];
export async function warEvents(ctx:CommandContext){
 const guild=requireGuildId(ctx),permissions=ctx.interaction.member?.permissions??"0";
 if(!/^\d+$/u.test(permissions)||(BigInt(permissions)&40n)===0n)throw new CommandInputError("Manage Server is required for war events.");
 const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale),action=stringOption(ctx,"action"),path=`/v2/server/${guild}/clan/${encodeURIComponent(tag)}/war-events`;
 if(!["view","enable","disable"].includes(action??""))throw new CommandInputError("Choose View, Enable or Disable.");
 const result=action==="view"?await ctx.services.api.get<{enabled:boolean}>(path):await ctx.services.api.put<{enabled:boolean}>(path,{enabled:action==="enable"});
 return legacyMessage({allowed_mentions:{parse:[]},content:`Automatic war events for ${tag}: **${result.enabled?"Enabled":"Disabled"}**.\n${result.enabled?"ClashKing needs Create Events permission. It creates a Discord event during preparation (or recovers the active war after downtime), ending when the war ends.":"Existing Discord events are left in place; no new ones will be created."}`},{ephemeral:true});
}
