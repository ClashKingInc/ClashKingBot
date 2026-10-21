import { escapeMarkdown, playerAppUrl, type Player } from "./game-common";
import type { CommandContext } from "./types";

interface Clan {tag:string;name:string}
interface Visit {clan:Clan;start:string;end?:string;role?:string}
interface HistoryView {description:string;footer:string}
const link=(clan:Clan)=>`[${escapeMarkdown(clan.name||clan.tag)}](https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(clan.tag)})`;
const timestamp=(value:string)=>`<t:${Math.floor(Date.parse(value)/1000)}:D>`;
const span=(minutes:number)=>{
 let days=Math.floor(minutes/1440);const years=Math.floor(days/365);days-=years*365;const months=Math.floor(days/30);days-=months*30;
 return [years?`${years} Years`:"",months?`${months} Months`:"",days?`${days} Days`:""].filter(Boolean).join(", ")||"N/A";
};
function format(count:number,full:string,totals:Array<{clan:Clan;minutes:number}>,visits:Visit[],footer:string):HistoryView{
 const longest=totals.slice(0,5).map(row=>`${link(row.clan)} - ${span(row.minutes)}`).join("\n")||"No Clans Found";
 const latest=visits.slice(0,5).map(visit=>{
  const days=visit.end?Math.floor((Date.parse(visit.end)-Date.parse(visit.start))/86400000):0;
  return `${link(visit.clan)}${visit.role?`, ${visit.role}`:""}${days>=1?`, ${days} days`:""}\n${visit.end?`${timestamp(visit.start)} to ${timestamp(visit.end)}`:`Seen on ${timestamp(visit.start)}`}`;
 }).join("\n")||"No Clans Found";
 return {description:`This player has been seen in a total of ${count} different clans\n[Full History](${full})\n\n**Top 5 Clans Player has stayed the most:**\n${longest}\n\n**Last 5 Clans Player has been seen at:**\n${latest}`,footer};
}
export async function clashKingHistory(ctx:CommandContext,player:Player):Promise<HistoryView>{
 const encoded=encodeURIComponent(player.tag);
 const [totals,events]=await Promise.all([
  ctx.services.api.get<{items:Array<{clan:Clan;minutes:number}>}>(`/v2/player/${encoded}/join-leave/totals`),
  ctx.services.api.get<{items:Array<{time:string;type:string;clan:Clan}>}>(`/v2/bot/players/${encoded}/clan-history`),
 ]);
 const chronological=[...events.items].sort((a,b)=>Date.parse(a.time)-Date.parse(b.time));
 const visits:Visit[]=[];
 for(let i=0;i<chronological.length;i++){
  const event=chronological[i]!;if(event.type!=="join")continue;
  const next=chronological.slice(i+1).find(row=>row.type==="join"||(row.type==="leave"&&row.clan.tag===event.clan.tag));
  // Use only observed boundaries. An unmatched join is a sighting, not an
  // invented continuous stay through today. Historical roles are not stored.
  visits.push({clan:event.clan,start:event.time,...(next?{end:next.time}:{})});
 }
 return format(totals.items.length,playerAppUrl(player.tag,ctx.env.APP_ENV),totals.items,visits.reverse(),"Data from ClashKing");
}
interface CosHistory {
 error?:unknown;
 clansMap?:Record<string,{name:string}>;
 summary?:Array<{tag:string;duration:number}>;
 log?:Array<{type:string;tag:string;role?:string;start?:string;end?:string;date?:string}>;
}
export async function clashOfStatsHistory(ctx:CommandContext,player:Player):Promise<HistoryView>{
 const full=`https://www.clashofstats.com/players/${encodeURIComponent(player.tag.slice(1))}/history/`;
 const unavailable={description:`Clash of Stats history is currently unavailable.\n[Full History](${full})`,footer:"Data from ClashofStats.com"};
 try{
  const userAgent=ctx.env.CLASHOFSTATS_USER_AGENT;
  if(!userAgent){if(ctx.env.APP_ENV==="dev")console.info("clash_of_stats_history",{headerConfigured:false});return unavailable;}
  const response=await fetch(`https://api.clashofstats.com/players/${encodeURIComponent(player.tag.slice(1))}/history/clans`,{headers:{"User-Agent":userAgent},signal:AbortSignal.timeout(8000),redirect:"manual"});
  if(ctx.env.APP_ENV==="dev")console.info("clash_of_stats_history",{headerConfigured:true,status:response.status,challenge:response.headers.get("cf-mitigated")==="challenge"});
  // Access denial is not evidence that this player's history is private.
  if(!response.ok)return unavailable;
  const raw=await response.text();if(raw.length>2_000_000)return unavailable;
  const data=JSON.parse(raw) as CosHistory;
  if(data.error)return /private/i.test(JSON.stringify(data.error))?{description:"This player has made their clash of stats history private.",footer:"Data from ClashofStats.com"}:unavailable;
  if(!Array.isArray(data.log)||!Array.isArray(data.summary))return unavailable;
  const clan=(tag:string):Clan=>({tag:tag.startsWith("#")?tag:`#${tag}`,name:data.clansMap?.[tag]?.name??tag});
  const roles:Record<string,string>={member:"Member",elder:"Elder",admin:"Co-Leader",coLeader:"Co-Leader",leader:"Leader"};
  const visits=data.log.filter(row=>row.tag).slice(0,5).flatMap(row=>{
   const start=row.type==="STAY"?row.start:row.type==="SEEN"?row.date:undefined;
   if(!start||!Number.isFinite(Date.parse(start)))return [];
   return [{clan:clan(row.tag),start,...(row.type==="STAY"&&row.end&&Number.isFinite(Date.parse(row.end))?{end:row.end}:{}),role:roles[row.role??""]}];
  });
  return format(new Set(data.log.map(row=>row.tag)).size,full,data.summary.map(row=>({clan:clan(row.tag),minutes:row.duration/60000})),visits,"Data from ClashofStats.com");
 }catch{return unavailable;}
}
