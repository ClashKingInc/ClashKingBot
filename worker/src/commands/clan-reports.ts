import { actionRow, legacyMessage, type LegacyEmbed } from "../discord/components";
import { ClashKingApiError } from "../api/client";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { currentRaidWeekend, loadRaidWeekend, validateRaidWeekend } from "./raid-data";
import { displayNameColumn } from "./display-width";
import { warTime } from "./war-data";
import type { ApplicationCommandOption, CommandContext } from "./types";
export const capitalOptions:ApplicationCommandOption[]=[
 {name:"weekend",description:"Friday date YYYY-MM-DD (defaults to latest raid weekend)",type:OptionType.String,autocomplete:true},
];
export const warLogOptions:ApplicationCommandOption[]=[
 {name:"view",description:"History to display",type:OptionType.String,choices:[{name:"War log",value:"wars"},{name:"CWL seasons",value:"cwl"}]},
 {name:"limit",description:"Most recent rows (default 15)",type:OptionType.Integer,min_value:1,max_value:25},
];
interface Clan{tag:string;name:string;memberList:Array<{tag:string}>;badgeUrls?:{small?:string;medium?:string}}
interface LogSide{tag:string;name:string;stars:number;destructionPercentage:number;attacks?:number;expEarned?:number}
interface LogEntry{endTime:string;teamSize:number;attacksPerMember?:number;type?:string;clan:LogSide;opponent?:LogSide;result?:string}
const clean=(value:string)=>escapeMarkdown(value.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"")).slice(0,80);
const pack=(lines:string[])=>{let text="",count=0;for(const line of lines){if(text.length+line.length+2>3700)break;text+=(text?"\n\n":"")+line;count++;}return {text,count};};
export async function clanReports(ctx:CommandContext){
 const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale),action=ctx.path[0],capital=action==="capital";
 const view=stringOption(ctx,"view")??(capital?"overview":"wars"),limit=capital?50:Number(ctx.options.get("limit")?.value??15),order=capital?"desc":stringOption(ctx,"sort_order")??"desc",currentOnly=capital?false:ctx.options.get("current_members")?.value===true;
 if(!Number.isInteger(limit)||limit<1||limit>(capital?50:25)||!["asc","desc"].includes(order)||!(capital?["overview","raiders","donations"]:["wars","cwl"]).includes(view))throw new CommandInputError("Choose valid clan report options.");
 const explicit=stringOption(ctx,"weekend"),weekend=capital?validateRaidWeekend(explicit??currentRaidWeekend()):"current";
 const clan=await ctx.services.api.get<Clan>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`),emoji=await emojis(ctx);
 const current=new Set(clan.memberList.map(member=>member.tag));
 let image:Uint8Array|undefined;
 let fields:NonNullable<LegacyEmbed["fields"]>=[];
 let lines:string[]=[],note="",empty="No recorded data for these options.";
 if(capital){
  if(view==="donations"){
   const result=await ctx.services.api.get<{start:string;end:string;truncated:boolean;items:Array<{tag:string;name:string;donated:number}>}>(`/v2/bot/clans/${encodeURIComponent(tag)}/capital-contributions`,{weekend});
   const selected=result.items.filter(row=>!currentOnly||current.has(row.tag)).sort((a,b)=>(order==="desc"?-1:1)*(a.donated-b.donated)||a.tag.localeCompare(b.tag));
   lines=selected.slice(0,limit).map(row=>`${emoji.get("capital_gold")}\`${String(row.donated).padStart(6)} ${displayNameColumn(row.name,15)}\``);
   note=`${currentOnly?"Current members":"All contributors"}${result.truncated?" — Partial data":""}`;
  }else{
   const raid=await loadRaidWeekend(ctx,tag,weekend);
   if(raid){const {capitalResult}=await import("./capital-result");image=await capitalResult(raid,clan);}
   empty="No raid data is available for this weekend.";
   note="";
   if(raid&&view==="raiders"){
    empty=raid.members?"No raiders matched these filters.":"Raid member data unavailable.";
    const selected=(raid.members??[]).filter(row=>!currentOnly||current.has(row.tag)).sort((a,b)=>(order==="desc"?-1:1)*(a.capitalResourcesLooted-b.capitalResourcesLooted)||a.tag.localeCompare(b.tag));
    lines=selected.slice(0,limit).map(row=>`${emoji.get("capital_gold")}\`${row.attacks}/${row.attackLimit+row.bonusAttackLimit} ${String(row.capitalResourcesLooted).padStart(6)} ${displayNameColumn(row.name,15)}\``);
   }else if(raid){
    const totalAttacks=(raid.members??[]).reduce((sum,member)=>sum+member.attacks,0);
    const timestamp=(value:string)=>`<t:${Math.floor(warTime(value)/1000)}:R>`;
    const format=(value:number)=>value.toLocaleString("en-US");
    fields.push({name:"Overview",value:[
     `${emoji.get("capital_gold")} ${format(raid.capitalTotalLoot)} Looted`,
     `${emoji.get("District_Hall5")} ${raid.enemyDistrictsDestroyed} Districts Destroyed`,
     `${emoji.get("thick_capital_sword")} ${totalAttacks}/300 Attacks Complete`,
     `${emoji.get("people")} ${raid.members?.length??0}/50 Participants`,
     `Start ${timestamp(raid.startTime)}, End ${timestamp(raid.endTime)}`,
    ].join("\n"),inline:false});
    const raids=raid.attackLog?.length??0,players=raid.members?.length??0;
    fields.push({name:"Detailed Stats (Offense)",value:[
     `Avg Loot/Raid: **${raids?format(Math.floor(raid.capitalTotalLoot/raids)):"—"}**`,
     `Avg Loot/Player: **${players?format(Math.floor(raid.capitalTotalLoot/players)):"—"}**`,
     `Avg Hits/Clan: **${raids?(totalAttacks/raids).toFixed(2):"—"}**`,
    ].join("\n"),inline:false});
    const averages=(entries:typeof raid.attackLog)=>{
     const districts=new Map<string,number[]>();
     for(const entry of entries??[])for(const district of entry.districts){if(!district.attacks)continue;const values=districts.get(district.name)??[];values.push(district.attacks.length);districts.set(district.name,values);}
     return [...districts].map(([name,values])=>`${(values.reduce((sum,n)=>sum+n,0)/values.length).toFixed(2).padStart(5)} ${name}`).join("\n");
    };
    for(const [label,entries] of [["Off",raid.attackLog],["Def",raid.defenseLog]] as const){
     const table=averages(entries);
     if(table)fields.push({name:`Avg Atks By District (${label})`,value:`\`\`\`\n${table.slice(0,990)}\n\`\`\``,inline:true});
    }
    // Raid opponents are nested by side in the Clash API, never entry.name.
    for(const [label,entries,side] of [["Attack Summary",raid.attackLog,"defender"],["Defense Summary",raid.defenseLog,"attacker"]] as const){
     const table=(entries??[]).map(entry=>`${displayNameColumn(entry[side]?.name??"Unavailable",12)} ${String(entry.attackCount??0).padStart(2)}a ${entry.districtsDestroyed??0}d ${compact(entry.districts.reduce((sum,d)=>sum+(d.totalLooted??0),0))}l`).join("\n");
     if(table)fields.push({name:label,value:`\`\`\`a=atks, d=districts, l=loot\n${table.slice(0,950)}\n\`\`\``,inline:false});
    }
    const top=[...(raid.members??[])].sort((a,b)=>b.capitalResourcesLooted-a.capitalResourcesLooted).slice(0,3);
    if(top.length)fields.push({name:"Top 3 Raiders",value:top.map((member,index)=>`${index+1}. **${clean(member.name)}** ${emoji.get("capital_gold")} ${format(member.capitalResourcesLooted)} (${member.attacks} attacks)`).join("\n"),inline:false});

   }
  }
 }else if(view==="cwl"){
  const result=await ctx.services.api.get<{items:Array<{season:string;state:string;warLeague?:{name:string}|null;rank:number|null;stars:number|null;warSize:number|null}>}>(`/v2/cwl/${encodeURIComponent(tag)}/seasons`,{limit});
  lines=[...result.items].sort((a,b)=>b.season.localeCompare(a.season)).slice(0,limit).map(row=>`**${row.season.slice(0,7)} — ${clean(row.warLeague?.name||"League unavailable")}**\n${row.rank===null?"Rank unavailable":`Group #${row.rank}`} — ${row.stars===null?"Stars unavailable":`${row.stars} stars`}${row.warSize?` — ${row.warSize}v${row.warSize}`:""} — ${clean(row.state)}`);
  note="";
 }else{
  let items:LogEntry[],source="";
  try{items=(await ctx.services.api.get<{items:LogEntry[]}>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}/warlog`,{limit})).items;}
  catch(error){
   if(!(error instanceof ClashKingApiError)||![403,404,502,503,504].includes(error.status))throw error;
   items=(await ctx.services.api.get<{items:LogEntry[]}>(`/v2/clan/${encodeURIComponent(tag)}/warlog`,{limit})).items;
   source=error.status===403?"War log private — Saved wars":"Saved wars — Live log unavailable";
  }
  lines=items.filter(row=>row.opponent?.tag&&row.type!=="cwl").sort((a,b)=>warTime(b.endTime)-warTime(a.endTime)).slice(0,limit).map(row=>{
   const own=row.clan.tag===tag?row.clan:row.opponent!,opponent=row.clan.tag===tag?row.opponent!:row.clan;
   const delta=own.stars-opponent.stars||own.destructionPercentage-opponent.destructionPercentage;
   const result=delta>0?"Win":delta<0?"Loss":"Draw",status=emoji.get(delta>0?"up_green_arrow":delta<0?"down_red_arrow":"grey_dash");
   const attacksPerMember=row.attacksPerMember??2,capacity=row.teamSize*attacksPerMember,end=warTime(row.endTime);
   const suffix=String(attacksPerMember).replace(/\d/gu,digit=>"⁰¹²³⁴⁵⁶⁷⁸⁹"[Number(digit)]!);
   return `${status} **${result} vs ${clean(opponent.name)}**\n(${row.teamSize} vs ${row.teamSize})${suffix}${Number.isFinite(end)?` | <t:${Math.floor(end/1000)}:R>`:""}\n${own.stars} ★ ${opponent.stars}${own.attacks===undefined?"":` | ${own.attacks}/${capacity}`} | ${own.destructionPercentage.toFixed(1)}%${own.expEarned===undefined?"":` | +${own.expEarned} XP`}`;

  });note=source;
 }
 const packed=pack(lines);
 if(capital&&view!=="overview")packed.text=lines.join("\n").slice(0,4000);
 const capitalId=(selected:string)=>["ck","page","cc",invokingUserId(ctx),tag,selected,explicit??"current","0"].join(":");
 const id=["ck","page","cr",invokingUserId(ctx),tag,action,view,"current",String(limit),order,currentOnly?"members":"all","0"].join(":");
 const refresh={type:2 as const,style:2 as const,emoji:emoji.component("refresh")??{name:"↻"},custom_id:capital?capitalId(view):id};
 const controls=capital?[actionRow(...([ ["overview","Overview"],["raiders","Raiders"],["donations","Donations"] ] as const).map(([key,label])=>({type:2 as const,style:key===view?1 as const:2 as const,label,custom_id:capitalId(key),disabled:key===view})),{...refresh,custom_id:capitalId(view).replace(/:0$/u,":1")} )]:[actionRow(refresh)];
 const response=legacyMessage({allowed_mentions:{parse:[]},embeds:[{...(capital?{author:{name:view==="overview"?`${clan.name} Raid Overview`:clan.name,...(clan.badgeUrls?.small?{icon_url:clan.badgeUrls.small}:{})},...(view==="overview"?{}:{title:view==="raiders"?"Raid Totals":"Donation Totals"})}:view==="cwl"?{title:`${clean(clan.name)} (CWL history)`,...(clan.badgeUrls?.small?{thumbnail:{url:clan.badgeUrls.small}}:{})}:{author:{name:`${clan.name} War Log (Last ${packed.count})`,...(clan.badgeUrls?.small?{icon_url:clan.badgeUrls.small}:{})}}),...(image?{image:{url:"attachment://raid-weekend.png"}}:{}),color:await serverEmbedColor(ctx),...(fields.length?{fields}:{description:packed.text||empty}),footer:{text:[capital?weekend:"",note,...(fields.length?[]:[`${packed.count} ${view==="wars"?"wars":view==="cwl"?"seasons":"entries"}`])].filter(Boolean).join(" | ")}}],components:controls});
 if(capital)response.data!.attachments=[];
 if(image){response.data!.__files=[{name:"raid-weekend.png",bytes:image}];}
 return response;
}
