import { displayNameColumn } from "./display-width";
import { actionRow, legacyMessage, type LegacyEmbed } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, stringOption } from "./command-utils";
import { compact, emojis } from "./game-common";
import { currentReportMembers } from "./report-members";
import type { Raid } from "./raid-data";
import { warTime } from "./war-data";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const metrics={
 gold:{label:"Gold looted",icon:"gold",group:"loot"},elixir:{label:"Elixir looted",icon:"elixir",group:"loot"},darkElixir:{label:"Dark Elixir looted",icon:"dark_elixir",group:"loot"},
 activity:{label:"Activity",icon:"clock",group:"loot"},
 donated:{label:"Donated troops",icon:"up_green_arrow",group:"contributions"},received:{label:"Received troops",icon:"down_red_arrow",group:"contributions"},clanGames:{label:"Clan Games points",icon:"clan_games",group:"contributions"},
 capitalDonated:{label:"Capital Gold donated",icon:"capital_gold",group:"capital"},capitalRaided:{label:"Capital Gold looted",icon:"capital_gold",group:"capital"},
 warStars:{label:"War stars",icon:"war_star",group:"competitive"},
} as const;
type Metric=keyof typeof metrics;
interface Item {tag:string;activity?:number|null;attacks:number|null;wins:number|null;gold:number|null;elixir:number|null;darkElixir:number|null;donated:number|null;received:number|null;capitalDonated:number|null;clanGames:number|null;warStars:number|null;trophies:number|null;snapshotDate:string|null;capitalRaided?:number|null}
interface Summary {season:string;start:string;end:string;warCoverageComplete:boolean;items:Item[]}
export const seasonSummaryOptions:ApplicationCommandOption[]=[
 {name:"season",description:"Game season YYYY-MM (default current)",type:OptionType.String},
 {name:"limit",description:"Top players per category (default 10)",type:OptionType.Integer,min_value:3,max_value:15},
];
export async function seasonSummary(ctx:CommandContext,scope:"clan"|"family"){
 const season=stringOption(ctx,"season")??"current",limit=Number(ctx.options.get("limit")?.value??10),hall=0;
 if(season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!Number.isInteger(limit)||limit<3||limit>15||!Number.isInteger(hall)||hall<0||hall>30)throw new CommandInputError("Choose valid summary options.");
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
 if(clans.length){
  try{
   const activity=await ctx.services.api.post<{truncated:boolean;items:Array<{tag:string;activity:number}>}>("/v2/bot/clans/activity",{clanTags:clans.map(clan=>clan.tag),...(season==="current"?{}:{season})});
   if(!activity.truncated)for(const row of activity.items){const item=items.get(row.tag);if(item)item.activity=row.activity;}
  }catch{failedPlayers++;}
 }
 if(window){
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
 const selected=Object.entries(metrics) as Array<[Metric,typeof metrics[Metric]]>;
 const emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const sections:Array<{text:string;group:string}>=[];
 for(const [key,metric] of selected){
  // Empty and zero-only categories add no useful information to a summary.
  const available=members.flatMap(member=>{const value=items.get(member.tag)?.[key];return typeof value==="number"&&value>0?[{member,value}]:[];}).sort((a,b)=>b.value-a.value||a.member.name.localeCompare(b.member.name)||a.member.tag.localeCompare(b.member.tag));
  if(!available.length)continue;
  const top=available.slice(0,limit);
  const valueWidth=Math.max(...top.map(row=>compact(row.value).length));
  const text=`**${emoji.get(metric.icon)} ${metric.label}**\n`+top.map((row,index)=>`\`${String(index+1).padStart(2)} ${compact(row.value).padStart(valueWidth)} ${displayNameColumn(row.member.name,15,22)}\``).join("\n");
  sections.push({text,group:metric.group});
 }
 const clanName=scope==="family"?"Family":clans[0]?.name??target;
 const guild=scope==="family"?await ctx.services.discordRest.getGuild(target):undefined;
 const author={...(typeof guild?.icon==="string"?{icon_url:`https://cdn.discordapp.com/icons/${target}/${guild.icon}.png`}:{}),name:`${guild?.name??clanName} Season Summary (${window?.season??season})`,...(scope==="clan"&&clans[0]?.badgeUrls?.small?{icon_url:clans[0].badgeUrls.small}:{})};
 const footer=`${members.length} current members${failedClans||failedPlayers?" | Some data unavailable":""}${!warComplete||raidIncomplete?" | Partial war/raid history":""}`;
 const embeds:LegacyEmbed[]=[];
 let text="",lastGroup="",total=author.name.length+footer.length;
 for(const section of sections){
  // Keep the old two-part layout where it fits, splitting only at category boundaries.
  if(text&&(text.length+section.text.length+2>3900||lastGroup==="loot"&&section.group!=="loot")){
   embeds.push({color,description:text});text="";
  }
  if(total+section.text.length+2>5800)throw new CommandInputError("This summary is too large. Choose a smaller limit.");
  text+=(text?"\n\n":"")+section.text;total+=section.text.length+2;lastGroup=section.group;
 }
 if(text)embeds.push({color,description:text});
 if(!embeds.length)embeds.push({color,description:"No recorded activity for this season."});
 embeds[0]!.author=author;
 if(scope==="family")for(const embed of embeds)embed.author=author;
 embeds[embeds.length-1]!.footer={text:footer};
 const id=["ck","page",scope==="clan"?"sc":"sf",invokingUserId(ctx),...(scope==="clan"?[target]:[]),season,String(limit),"0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id})]});
}
