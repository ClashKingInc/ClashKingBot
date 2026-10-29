import { actionRow } from "../discord/components";
import { InteractionResponseType, InteractionType, MessageFlags } from "../discord/types";
import { CommandInputError, invokingUserId, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, gameReply, legendDay, pagedGameReply, playerUrl } from "./game-common";
import type { CommandContext } from "./types";

interface Cutoffs { day:string|null;items:Array<{rank:number;trophies:number}> }
interface Daily { day:string;attacks:number;players:number;starCounts:{zero:number;one:number;two:number;three:number};averageDestruction:number|null;averageDuration:number|null }
const count=(n:number)=>n.toLocaleString("en");
export async function globalLegendStats(ctx:CommandContext){
  const type=stringOption(ctx,"type")??"cutoffs",limit=Number(ctx.options.get("limit")?.value??50),emoji=await emojis(ctx);
  if(!["cutoffs","buckets","winners","daily","streaks"].includes(type)||!Number.isSafeInteger(limit)||limit<1||limit>50)throw new CommandInputError("Choose a valid statistic and a limit from 1 to 50.");
  const trophy=emoji.get("trophy"),star=emoji.get("star")||emoji.get("attack_star");
  let title="Legend Statistics",description="",entries:string[]|undefined;
  if(type==="streaks"){
    title="Legend Triple Streaks";
    const result=await ctx.services.api.get<{items:Array<{tag:string;name:string;streak:number;observedSince:string;lastAttackAt:string;resetObserved:boolean}>}>("/v2/bot/legends/stats",{type:"streaks",limit});
    // These are consecutive recorded attacks, not proof that every game attack
    // was observed. Never present a retained-history bootstrap as lifetime data.
    description="No recorded triple streaks yet.";
    entries=result.items.map((row,index)=>`**#${index+1} · ${star} ${row.resetObserved?"":"≥"}${count(row.streak)}** [${escapeMarkdown(row.name)}](${playerUrl(row.tag)})\n-# Last triple <t:${Math.floor(Date.parse(row.lastAttackAt)/1000)}:R>`);
  }else if(type==="cutoffs"||type==="buckets"){
    const cutoff=await ctx.services.api.get<Cutoffs>("/v2/bot/legends/stats",{type:"cutoffs"});
    description=cutoff.day?`**${cutoff.day}**\n`:"No stored ranking snapshot is available.";
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
    description="No season winners are available yet.";
  }else if(type==="daily"){
    title="Legend Daily Performance";
    const last=new Date(Date.parse(legendDay())-86400000).toISOString().slice(0,10),first=new Date(Date.parse(last)-6*86400000).toISOString().slice(0,10);
    const cohorts=[{id:"legend_i",name:"Legend I"},{id:"top_1000",name:"Top 1,000"},{id:"top_200",name:"Top 200"}];
    const results=await Promise.all(cohorts.map(async cohort=>({cohort,result:await ctx.services.api.get<{items:Daily[]}>("/v2/stats/legend/days",{"time[after]":first,"time[before]":last,cohort:cohort.id})})));
    description=`**${first} – ${last}**\n`;
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
  response.data!.components = [...(Array.isArray(response.data?.components) ? response.data.components : []), actionRow({
    type: 3, custom_id: `ck:legendstats:${limit}`, placeholder: "Legend statistics",
    options: Object.entries(legendViews).map(([value, label]) => ({ label, value, default: value === type })),
  })];
  return response;
}

const legendViews = { streaks: "Triple streaks", cutoffs: "Rank cutoffs", buckets: "Trophy distribution", winners: "Season winners", daily: "Daily performance" };
export async function dispatchLegendStats(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  const match = /^ck:legendstats:([1-9][0-9]?)$/u.exec(ctx.interaction.data?.custom_id ?? "");
  const selected = ctx.interaction.data?.values?.[0];
  if (ctx.interaction.type !== InteractionType.MessageComponent || ctx.interaction.data?.component_type !== 3 || ctx.interaction.data.values?.length !== 1 || !match || Number(match[1]) > 50 || !selected || !Object.hasOwn(legendViews, selected))
    throw new CommandInputError("Choose a Legend statistic.");
  const run = () => globalLegendStats({ ...ctx, options: new Map([
    ["type", { name: "type", type: 3, value: selected }],
    ["limit", { name: "limit", type: 4, value: Number(match[1]) }],
  ]) });
  if (!waitUntil) return { ...(await run()), type: InteractionResponseType.UpdateMessage };
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {})).catch(() =>
    ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token, { content: "Couldn't load these statistics. Please try again.", flags: MessageFlags.Ephemeral })));
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
