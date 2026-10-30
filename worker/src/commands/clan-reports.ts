import { actionRow, legacyMessage } from "../discord/components";
import { ClashKingApiError } from "../api/client";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { currentRaidWeekend, loadRaidWeekend, validateRaidWeekend } from "./raid-data";
import { warTime } from "./war-data";
import type { ApplicationCommandOption, CommandContext } from "./types";
export const capitalOptions:ApplicationCommandOption[]=[
 {name:"view",description:"Capital report (default Overview)",type:OptionType.String,choices:[{name:"Overview",value:"overview"},{name:"Raiders",value:"raiders"},{name:"Donations",value:"donations"}]},
 {name:"weekend",description:"Friday date YYYY-MM-DD (defaults to latest raid weekend)",type:OptionType.String},
 {name:"limit",description:"Maximum player rows (default 30)",type:OptionType.Integer,min_value:1,max_value:50},
 {name:"sort_order",description:"Loot/donation order",type:OptionType.String,choices:[{name:"Highest first",value:"desc"},{name:"Lowest first",value:"asc"}]},
 {name:"current_members",description:"Only current clan members (default false)",type:OptionType.Boolean},
];
export const warLogOptions:ApplicationCommandOption[]=[
 {name:"view",description:"History to display",type:OptionType.String,choices:[{name:"War log",value:"wars"},{name:"CWL seasons",value:"cwl"}]},
 {name:"limit",description:"Most recent rows (default 15)",type:OptionType.Integer,min_value:1,max_value:25},
];
interface Clan{tag:string;name:string;memberList:Array<{tag:string}>;badgeUrls?:{small?:string}}
interface LogSide{tag:string;name:string;stars:number;destructionPercentage:number;attacks?:number}
interface LogEntry{endTime:string;teamSize:number;attacksPerMember?:number;type?:string;clan:LogSide;opponent?:LogSide;result?:string}
const clean=(value:string)=>escapeMarkdown(value.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"")).slice(0,80);
const pack=(lines:string[])=>{let text="",count=0;for(const line of lines){if(text.length+line.length+2>3700)break;text+=(text?"\n\n":"")+line;count++;}return {text,count};};
export async function clanReports(ctx:CommandContext){
 const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale),action=ctx.path[0],capital=action==="capital";
 const view=stringOption(ctx,"view")??(capital?"overview":"wars"),limit=Number(ctx.options.get("limit")?.value??(capital?30:15)),order=stringOption(ctx,"sort_order")??"desc",currentOnly=ctx.options.get("current_members")?.value===true;
 if(!Number.isInteger(limit)||limit<1||limit>(capital?50:25)||!["asc","desc"].includes(order)||!(capital?["overview","raiders","donations"]:["wars","cwl"]).includes(view))throw new CommandInputError("Choose valid clan report options.");
 const explicit=stringOption(ctx,"weekend"),weekend=capital?validateRaidWeekend(explicit??currentRaidWeekend()):"current";
 const clan=await ctx.services.api.get<Clan>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`),emoji=await emojis(ctx);
 const current=new Set(clan.memberList.map(member=>member.tag));
 let lines:string[]=[],note="",empty="No recorded data for these options.";
 if(capital){
  if(view==="donations"){
   const result=await ctx.services.api.get<{start:string;end:string;truncated:boolean;items:Array<{tag:string;name:string;donated:number}>}>(`/v2/bot/clans/${encodeURIComponent(tag)}/capital-contributions`,{weekend});
   const selected=result.items.filter(row=>!currentOnly||current.has(row.tag)).sort((a,b)=>(order==="desc"?-1:1)*(a.donated-b.donated)||a.tag.localeCompare(b.tag));
   lines=selected.slice(0,limit).map((row,index)=>`**${index+1}. ${clean(row.name)}** · ${emoji.get("capital_gold")} ${compact(row.donated)}${current.has(row.tag)?"":" · former member"}`);
   note=`${currentOnly?"Current members":"All contributors"}${result.truncated?" · Partial data":""}`;
  }else{
   const raid=await loadRaidWeekend(ctx,tag,weekend);
   empty="No raid data is available for this weekend.";
   note="";
   if(raid&&view==="raiders"){
    empty=raid.members?"No raiders matched these filters.":"Raid member data unavailable.";
    const selected=(raid.members??[]).filter(row=>!currentOnly||current.has(row.tag)).sort((a,b)=>(order==="desc"?-1:1)*(a.capitalResourcesLooted-b.capitalResourcesLooted)||a.tag.localeCompare(b.tag));
    lines=selected.slice(0,limit).map((row,index)=>`**${index+1}. ${clean(row.name)}** · ${emoji.get("capital_gold")} ${compact(row.capitalResourcesLooted)}\n${row.attacks}/${row.attackLimit+row.bonusAttackLimit} attacks${current.has(row.tag)?"":" · former member"}`);
   }else if(raid){
    lines=[`**${raid.state==="ongoing"?"Ongoing":"Ended"} raid** · ${raid.totalAttacks} attacks · ${raid.members?`${raid.members.length} participants`:"Participants unavailable"}`,`${emoji.get("capital_gold")} **${compact(raid.capitalTotalLoot)} looted** · ${raid.enemyDistrictsDestroyed} districts destroyed · ${raid.raidsCompleted} raids completed`];
    const averages=(entries:typeof raid.attackLog)=>{const districts=new Map<string,number[]>();for(const entry of entries??[])for(const district of entry.districts){if(!district.attacks)continue;const values=districts.get(district.name)??[];values.push(district.attacks.length);districts.set(district.name,values);}return [...districts].map(([name,values])=>`${clean(name)}: ${(values.reduce((sum,n)=>sum+n,0)/values.length).toFixed(1)}`).join("\n");};
    const offense=averages(raid.attackLog),defense=averages(raid.defenseLog);
    if(offense)lines.push(`**Average attacks per district · offense**\n${offense}`);
    if(defense)lines.push(`**Average attacks per district · defense**\n${defense}`);
   }
  }
 }else if(view==="cwl"){
  const result=await ctx.services.api.get<{items:Array<{season:string;state:string;warLeague?:{name:string}|null;rank:number|null;stars:number|null;warSize:number|null}>}>(`/v2/cwl/${encodeURIComponent(tag)}/seasons`,{limit});
  lines=[...result.items].sort((a,b)=>b.season.localeCompare(a.season)).slice(0,limit).map(row=>`**${row.season.slice(0,7)} · ${clean(row.warLeague?.name||"League unavailable")}**\n${row.rank===null?"Rank unavailable":`Group #${row.rank}`} · ${row.stars===null?"Stars unavailable":`${row.stars} stars`}${row.warSize?` · ${row.warSize}v${row.warSize}`:""} · ${clean(row.state)}`);
  note="";
 }else{
  let items:LogEntry[],source="";
  try{items=(await ctx.services.api.get<{items:LogEntry[]}>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}/warlog`,{limit})).items;}
  catch(error){
   if(!(error instanceof ClashKingApiError)||![403,404,502,503,504].includes(error.status))throw error;
   items=(await ctx.services.api.get<{items:LogEntry[]}>(`/v2/clan/${encodeURIComponent(tag)}/warlog`,{limit})).items;
   source=error.status===403?"War log private · Saved wars":"Saved wars · Live log unavailable";
  }
  lines=items.filter(row=>row.opponent?.tag).sort((a,b)=>warTime(b.endTime)-warTime(a.endTime)).slice(0,limit).map(row=>{
   const opponent=row.opponent!,delta=row.clan.stars-opponent.stars||row.clan.destructionPercentage-opponent.destructionPercentage;
   const result=delta>0?"Win":delta<0?"Loss":"Draw",end=warTime(row.endTime),capacity=row.teamSize*(row.attacksPerMember??(row.type==="cwl"?1:2));
   return `**${result} vs ${clean(opponent.name)}**${row.type?` · ${clean(row.type)}`:""}\n${row.clan.stars}–${opponent.stars} stars · ${row.clan.destructionPercentage.toFixed(1)}% · ${row.teamSize}v${row.teamSize}${row.clan.attacks===undefined?"":` · ${row.clan.attacks}/${capacity} attacks`}${Number.isFinite(end)?` · <t:${Math.floor(end/1000)}:R>`:""}`;
  });note=source;
 }
 const packed=pack(lines),id=["ck","page","cr",invokingUserId(ctx),tag,action,view,capital?explicit??"current":"current",String(limit),order,currentOnly?"members":"all","0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:`${clean(clan.name)} · ${capital?view==="donations"?"Capital donations":view==="raiders"?"Capital raiders":"Capital overview":view==="cwl"?"CWL history":"War log"}`,color:await serverEmbedColor(ctx),description:packed.text||empty,footer:{text:[capital?weekend:"",note,`${packed.count} ${view==="wars"?"wars":view==="cwl"?"seasons":"entries"}`].filter(Boolean).join(" · ")}}],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
