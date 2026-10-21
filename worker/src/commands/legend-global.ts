import { actionRow } from "../discord/components";
import { CommandInputError, invokingUserId, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, gameReply, legendDay, pagedGameReply, playerUrl } from "./game-common";
import type { CommandContext } from "./types";

interface Cutoffs { day:string|null;items:Array<{rank:number;trophies:number}> }
interface Daily { day:string;attacks:number;players:number;starCounts:{zero:number;one:number;two:number;three:number};averageDestruction:number|null;averageDuration:number|null }
const count=(n:number)=>n.toLocaleString("en");
export async function globalLegendStats(ctx:CommandContext){
  const type=stringOption(ctx,"type")??"cutoffs",limit=Number(ctx.options.get("limit")?.value??50),emoji=await emojis(ctx);
  if(!["cutoffs","buckets","winners","daily"].includes(type)||!Number.isSafeInteger(limit)||limit<1||limit>50)throw new CommandInputError("Choose a valid statistic and a limit from 1 to 50.");
  const trophy=emoji.get("trophy"),star=emoji.get("star")||emoji.get("attack_star");
  let title="Legend Statistics",description="",entries:string[]|undefined;
  if(type==="cutoffs"||type==="buckets"){
    const cutoff=await ctx.services.api.get<Cutoffs>("/v2/bot/legends/stats",{type:"cutoffs"});
    description=cutoff.day?`**Ranking snapshot: ${cutoff.day}**\n`:"No stored ranking snapshot is available.";
    if(type==="cutoffs"){
      title="Legend Rank Cutoffs";
      description+=cutoff.items.map(row=>`**#${count(row.rank)}** · ${trophy} ${count(row.trophies)}`).join("\n");
    }else{
      title="Legend Trophy Buckets";
      if(cutoff.day){
        const result=await ctx.services.api.get<{items:Array<{minimumTrophies:number;maximumTrophies:number;playerCount:number}>}>(`/v2/legends/trophy-buckets/${cutoff.day}`);
        const total=result.items.reduce((sum,row)=>sum+row.playerCount,0);
        description+=`${count(total)} ranked players\n\n`+result.items.filter(row=>row.playerCount).sort((a,b)=>b.minimumTrophies-a.minimumTrophies).map(row=>`${trophy} **${count(row.minimumTrophies)}–${count(row.maximumTrophies)}**\n${count(row.playerCount)} players · ${total?(row.playerCount/total*100).toFixed(1):"0"}%`).join("\n");
      }
    }
  }else if(type==="winners"){
    title="Legend Season Winners";
    const result=await ctx.services.api.get<{items:Array<{season:string;name:string;tag:string;trophies:number}>}>("/v2/bot/legends/stats",{type:"winners",limit});
    entries=result.items.map(row=>{
      const date=new Date(row.season.replace(/^v2-/u,""));
      const season=Number.isFinite(date.valueOf())?new Intl.DateTimeFormat("en",{month:"long",year:"numeric",timeZone:"UTC"}).format(date):row.season;
      return `**${season}**\n[${escapeMarkdown(row.name)}](${playerUrl(row.tag)}) · ${trophy} ${count(row.trophies)}`;
    });
    description="No first-place season finishes are stored locally.";
  }else if(type==="daily"){
    title="Legend Daily Performance";
    const last=new Date(Date.parse(legendDay())-86400000).toISOString().slice(0,10),first=new Date(Date.parse(last)-6*86400000).toISOString().slice(0,10);
    const cohorts=[{id:"legend_i",name:"Legend I"},{id:"top_1000",name:"Top 1,000"},{id:"top_200",name:"Top 200"}];
    const results=await Promise.all(cohorts.map(async cohort=>({cohort,result:await ctx.services.api.get<{items:Daily[]}>("/v2/stats/legend/days",{"time[after]":first,"time[before]":last,cohort:cohort.id})})));
    description=`**Closed-day data · ${first} – ${last}**\n`;
    for(const {cohort,result} of results){
      const row=[...result.items].sort((a,b)=>b.day.localeCompare(a.day))[0];
      description+=`\n**${cohort.name}${row?` · ${row.day}`:""}**\n`;
      if(!row){description+="No recorded cohort data.\n";continue;}
      description+=`${count(row.players)} players · ${count(row.attacks)} attacks\n${star} ${count(row.starCounts.three)} triples · ${row.attacks?(row.starCounts.three/row.attacks*100).toFixed(1):"0"}%\n${row.averageDestruction?.toFixed(1)??"—"}% destruction · ${row.averageDuration?.toFixed(0)??"—"}s average\n`;
    }
  }
  const response=entries?.length?await pagedGameReply(ctx,title,entries,"lg",[type,String(limit)]):await gameReply(ctx,title,description);
  // Do not reintroduce generic pagination/footer copy on this compact display.
  for(const embed of (response.data?.embeds??[]) as Array<{footer?:unknown}>)delete embed.footer;
  if(!((response.data?.components??[]) as unknown[]).length){
    const refresh=emoji.component("refresh");
    response.data!.components=[actionRow({type:2,style:2,emoji:refresh?{id:refresh.id,name:refresh.name,animated:refresh.animated}:{name:"🔄"},custom_id:["ck","page","lg",invokingUserId(ctx),type,String(limit),"0"].join(":")})];
  }
  return response;
}
