import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { currentReportMembers } from "./report-members";
import type { Raid } from "./raid-data";
import { warTime } from "./war-data";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const sections={all:"Overview",loot:"Loot and battles",contributions:"Donations and Clan Games",capital:"Capital Gold",competitive:"Wars and trophies"};
const metrics={
 gold:{label:"Gold looted",icon:"gold",group:"loot"},elixir:{label:"Elixir looted",icon:"elixir",group:"loot"},darkElixir:{label:"Dark Elixir looted",icon:"dark_elixir",group:"loot"},
 attacks:{label:"Attacks",icon:"clash_sword",group:"loot"},wins:{label:"Attack wins",icon:"war_star",group:"loot"},
 donated:{label:"Donated troops",icon:"up_green_arrow",group:"contributions"},received:{label:"Received troops",icon:"down_red_arrow",group:"contributions"},clanGames:{label:"Clan Games points",icon:"clan_games",group:"contributions"},
 capitalDonated:{label:"Capital Gold donated",icon:"capital_gold",group:"capital"},capitalRaided:{label:"Capital Gold looted",icon:"capital_gold",group:"capital"},
 warStars:{label:"War stars",icon:"war_star",group:"competitive"},trophies:{label:"Trophies",icon:"trophy",group:"competitive"},
} as const;
type Metric=keyof typeof metrics;
interface Item {tag:string;attacks:number|null;wins:number|null;gold:number|null;elixir:number|null;darkElixir:number|null;donated:number|null;received:number|null;capitalDonated:number|null;clanGames:number|null;warStars:number|null;trophies:number|null;snapshotDate:string|null;capitalRaided?:number|null}
interface Summary {season:string;start:string;end:string;warCoverageComplete:boolean;items:Item[]}
export const seasonSummaryOptions:ApplicationCommandOption[]=[
 {name:"view",description:"Summary section (default All)",type:OptionType.String,choices:Object.entries(sections).map(([value,name])=>({name,value}))},
 {name:"season",description:"Game season YYYY-MM (default current)",type:OptionType.String},
 {name:"limit",description:"Top players per metric (default 5)",type:OptionType.Integer,min_value:1,max_value:15},
 {name:"townhall",description:"Filter current members by Town Hall",type:OptionType.Integer,min_value:1,max_value:30},
];
export async function seasonSummary(ctx:CommandContext,scope:"clan"|"family"){
 const view=stringOption(ctx,"view")??"all",season=stringOption(ctx,"season")??"current",limit=Number(ctx.options.get("limit")?.value??5),hall=Number(ctx.options.get("townhall")?.value??0);
 if(!Object.hasOwn(sections,view)||season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!Number.isInteger(limit)||limit<1||limit>15||!Number.isInteger(hall)||hall<0||hall>30)throw new CommandInputError("Choose valid summary options.");
 const {target,clans,members,failedClans}=await currentReportMembers(ctx,scope,hall),items=new Map<string,Item>();let failedPlayers=0,window:Summary|undefined,warComplete=true;
 for(let i=0;i<members.length;i+=400){
  const batches=Array.from({length:Math.ceil(Math.min(400,members.length-i)/100)},(_,j)=>members.slice(i+j*100,i+(j+1)*100));
  const responses=await Promise.allSettled(batches.map(batch=>ctx.services.api.post<Summary>("/v2/bot/players/season-summary",{tags:batch.map(member=>member.tag),...(season==="current"?{}:{season})})));
  for(const [index,response] of responses.entries())if(response.status==="fulfilled"){
   if(window&&window.season!==response.value.season)throw new CommandInputError("The season changed while loading. Refresh this report.");
   window=response.value;warComplete&&=response.value.warCoverageComplete;for(const item of response.value.items)items.set(item.tag,item);
  }else failedPlayers+=batches[index]!.length;
 }
 let raidIncomplete=0;
 if(window&&(view==="capital"||view==="all")){
  const gold=new Map<string,number>(),wanted=new Set(members.map(member=>member.tag)),seen=new Set<string>();
  for(let i=0;i<clans.length;i+=4){const responses=await Promise.allSettled(clans.slice(i,i+4).map(clan=>ctx.services.api.get<{items:Raid[]}>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}/capitalraidseasons`,{limit:10})));
   for(const [index,response] of responses.entries()){
    if(response.status==="rejected"){raidIncomplete++;continue;}
    const dates=response.value.items.map(raid=>warTime(raid.startTime)).filter(Number.isFinite);
    if(dates.length>=10&&Math.min(...dates)>Date.parse(window.start))raidIncomplete++;
    for(const raid of response.value.items){const time=warTime(raid.startTime),key=`${clans[i+index]!.tag}:${raid.startTime}`;
     if(!Number.isFinite(time)||time<Date.parse(window.start)||time>=Date.parse(window.end)||seen.has(key))continue;seen.add(key);
     for(const member of raid.members??[])if(wanted.has(member.tag))gold.set(member.tag,(gold.get(member.tag)??0)+member.capitalResourcesLooted);
    }
   }
  }
  for(const [tag,item] of items)item.capitalRaided=raidIncomplete?null:gold.get(tag)??null;
 }
 const selected=(Object.entries(metrics) as Array<[Metric,typeof metrics[Metric]]>).filter(([,metric])=>view==="all"||metric.group===view),emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const budget=Math.min(1000,Math.floor(5000/selected.length)-70),fields:Array<{name:string;value:string;inline:false}>=[];let clipped=0;
 const clean=(name:string)=>escapeMarkdown(name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"")).slice(0,35);
 for(const [key,metric] of selected){
  const available=members.flatMap(member=>{const item=items.get(member.tag),value=item?.[key];return typeof value==="number"?[{member,value,item}]:[];}).sort((a,b)=>b.value-a.value||a.member.tag.localeCompare(b.member.tag));
  let text="",shown=0;
  for(const row of available.slice(0,limit)){const line=`**${shown+1}.** ${clean(row.member.name)} · **${compact(row.value)}**${key==="trophies"&&row.item?.snapshotDate?` (${row.item.snapshotDate})`:""}`;if(text.length+line.length+1>budget)break;text+=(text?"\n":"")+line;shown++;}
  clipped+=Math.min(limit,available.length)-shown;
  fields.push({name:`${emoji.get(metric.icon)} ${metric.label}`,value:text||"No recorded observations.",inline:false});
 }
 const title=`${scope==="family"?"Family":escapeMarkdown(clans[0]?.name??target).slice(0,80)} · ${window?.season??season} summary`;
 const footer=`${members.length} current members${failedClans||failedPlayers?" · Some members unavailable":""}${!warComplete||raidIncomplete?" · Partial war/raid history":""}${clipped?` · Top ${limit} per category`:""}`;
 const embeds=[];for(let i=0;i<fields.length;i+=6)embeds.push({title:i?`${title} (continued)`:title,color,fields:fields.slice(i,i+6),footer:{text:footer}});
 const id=["ck","page",scope==="clan"?"sc":"sf",invokingUserId(ctx),...(scope==="clan"?[target]:[]),view,season,String(limit),String(hall),"0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
