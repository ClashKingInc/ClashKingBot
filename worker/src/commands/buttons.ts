import { legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, requireGuildId } from "./command-utils";
import { playerCommand } from "./player";
import { refreshCommand } from "./refresh";
import type { CommandContext } from "./types";

// Published panels still resolve their current clicker. Creation belongs in the
// dashboard; retaining the interaction handler does not register a setup command.
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
