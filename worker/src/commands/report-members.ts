import { CommandInputError, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import type { CommandContext } from "./types";
export interface ReportMember{tag:string;name:string;townHallLevel?:number}
export interface ReportClan{tag:string;name:string;memberList:ReportMember[]}
export async function currentReportMembers(ctx:CommandContext,scope:"clan"|"family",hall=0){
 const target=scope==="clan"?normalizeTag(stringOption(ctx,"clan")??"",ctx.locale):requireGuildId(ctx);
 const refs=scope==="clan"?[{tag:target}]:await ctx.services.api.get<Array<{tag:string}>>(`/v2/server/${target}/clans-basic`);
 if(!refs.length)throw new CommandInputError("No family clans are linked to this server.");
 if(refs.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
 const clans:ReportClan[]=[];let failedClans=0;
 for(let i=0;i<refs.length;i+=5){const results=await Promise.allSettled(refs.slice(i,i+5).map(ref=>ctx.services.api.get<ReportClan>(`/v2/bot/clash/clans/${encodeURIComponent(ref.tag)}`)));for(const result of results)if(result.status==="fulfilled")clans.push(result.value);else failedClans++;}
 // Snapshot lag can leave one player listed by two clans. Player-based reports
 // must count that identity once, independently of where prior events occurred.
 const members=[...new Map(clans.flatMap(clan=>clan.memberList).map(member=>[member.tag,member])).values()].filter(member=>!hall||member.townHallLevel===hall);
 return {target,clans,members,failedClans};
}
