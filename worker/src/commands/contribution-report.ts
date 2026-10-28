import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, OptionType, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { CommandContext } from "./types";

export interface ContributionMember { tag:string; name:string; townHallLevel?:number; donations?:number; donationsReceived?:number }
export interface ContributionClan { tag:string; name:string; memberList:ContributionMember[] }
interface Row { tag:string; name:string; townHallLevel:number; donated:number; received:number; clanGames:number; capitalDonated:number }
interface Stats { season:string; current:boolean; truncated:boolean; items:Row[] }
export const contributionOptions = [
  {name:"limit",description:"Top players to show (default 30)",type:OptionType.Integer,min_value:1,max_value:50},
  {name:"sort_order",description:"Sort direction (default highest first)",type:OptionType.String,choices:[{name:"Highest first",value:"desc"},{name:"Lowest first",value:"asc"}]},
  {name:"townhall",description:"Only show this Town Hall",type:OptionType.Integer,min_value:1,max_value:30},
];
const clean=(name:string)=>escapeMarkdown(name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,""));
const pack=(lines:string[],budget:number)=>{let text="";let count=0;for(const line of lines){if(text.length+line.length+1>budget)break;text+=(text?"\n":"")+line;count++;}return {text,count};};
export async function contributionReport(ctx:CommandContext,clans:ContributionClan[],kind:"donations"|"games",family:boolean){
  const limit=Number(ctx.options.get("limit")?.value??30),hall=Number(ctx.options.get("townhall")?.value??0),order=stringOption(ctx,"sort_order")??"desc",sort=kind==="games"?"clanGames":stringOption(ctx,"sort_by")??"donated",season=stringOption(ctx,"season");
  const currentOnly=kind==="games"||ctx.options.get("current_members")?.value===true;
  if(!Number.isInteger(limit)||limit<1||limit>50||!Number.isInteger(hall)||hall<0||hall>30||!["asc","desc"].includes(order)||!["donated","received","ratio","clanGames"].includes(sort)||season&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))throw new CommandInputError("Choose valid contribution filters.");
  const combined=new Map<string,Row>(),totals:Array<{name:string;value:number}>=[];let partial=false;const seasons=new Set<string>();
  // Sum clan-attributed events once across the family. Current membership is
  // a display filter, not a substitute for where donations were recorded.
  const currentTags=new Set(clans.flatMap(clan=>clan.memberList.map(member=>member.tag)));
  for(let offset=0;offset<clans.length;offset+=5){
    const batch=await Promise.all(clans.slice(offset,offset+5).map(async clan=>{
      if(kind==="games"){
        const game=await ctx.services.api.get<{items:Array<{tag:string;points:number}>}>(`/v2/bot/clans/${encodeURIComponent(clan.tag)}/clan-games`,{},AbortSignal.timeout(15000));
        const points=new Map(game.items.map(row=>[row.tag,row.points]));
        return {clan,stats:{current:true,truncated:false,season:new Date().toISOString().slice(0,7),items:clan.memberList.map(member=>({tag:member.tag,name:member.name,townHallLevel:member.townHallLevel??0,donated:0,received:0,capitalDonated:0,clanGames:points.get(member.tag)??0}))}};
      }
      return {clan,stats:await ctx.services.api.get<Stats>(`/v2/bot/clans/${encodeURIComponent(clan.tag)}/season-stats`,season?{season}:{},AbortSignal.timeout(15000))};
    }));
    for(const {clan,stats} of batch){
      partial ||= stats.truncated;seasons.add(stats.season);
      const selected=stats.items.filter(row=>(!hall||row.townHallLevel===hall)&&(!currentOnly||currentTags.has(row.tag)));
      totals.push({name:clan.name,value:selected.reduce((sum,row)=>sum+(kind==="games"?row.clanGames:row.donated),0)});
      for(const row of selected){
        const previous=combined.get(row.tag);
        // Games follows the player across clans, so use their observed total;
        // donation events are attributed separately and must be summed.
        combined.set(row.tag,previous?{...previous,donated:previous.donated+row.donated,received:previous.received+row.received,clanGames:Math.max(previous.clanGames,row.clanGames)}:{...row});
      }
      if(stats.current)for(const member of clan.memberList)if((!hall||member.townHallLevel===hall)&&!combined.has(member.tag))combined.set(member.tag,{tag:member.tag,name:member.name,townHallLevel:member.townHallLevel??0,donated:0,received:0,clanGames:0,capitalDonated:0});
    }
  }
  const metric=(row:Row)=>sort==="ratio"?row.donated/Math.max(1,row.received):row[sort as "donated"|"received"|"clanGames"];
  const selected=[...combined.values()].sort((a,b)=>(order==="asc"?1:-1)*(metric(a)-metric(b))||a.tag.localeCompare(b.tag)).slice(0,limit);
  const emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
  const lines=selected.map((row,index)=>`**${index+1}.** ${emoji.get(row.townHallLevel)} \u2068${clean(row.name).slice(0,80)}\u2069 · ${kind==="games"?`${compact(row.clanGames)} pts`:sort==="ratio"?`${(row.donated/Math.max(1,row.received)).toFixed(2)} ratio · ↑${compact(row.donated)} ↓${compact(row.received)}`:`↑${compact(row.donated)} ↓${compact(row.received)}`}`);
  const packed=pack(lines,3300),title=`${family?"Family":clans[0]?.name??"Clan"} · ${kind==="games"?"Clan Games":"Donations"}`;
  const footer=[...seasons].join(", ")+` · ${packed.count}/${combined.size} players · ${currentOnly?"Current members":"Recorded contributors"}${partial?" · Partial recorded data":""}`;
  const embeds=[{title,color,description:packed.text||"No recorded contributions for these filters.",footer:{text:footer}}];
  if(family){const summary=pack(totals.sort((a,b)=>b.value-a.value).map(row=>`**${clean(row.name).slice(0,80)}** · ${compact(row.value)}`),1800);embeds.push({title:"Clan totals",color,description:summary.text||"No linked clans.",footer:{text:`${summary.count}/${clans.length} clans · ${kind==="games"?"Points earned by current members":"Recorded donations"}`}});}
  const values=[kind,season??"current",String(limit),order,String(hall),sort,currentOnly?"m":"a"];
  const id=["ck","page",family?"fm":"cg",invokingUserId(ctx),...(family?[]:[clans[0]!.tag]),...values,"0"].join(":");
  return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
