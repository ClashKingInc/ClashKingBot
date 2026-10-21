import { CommandInputError, OptionType, normalizeTag, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, fetchPlayer, pagedGameReply, legendDay, personalPlayerAutocomplete, playerOption, resolvePlayerTag, subcommand } from "./game-common";
import type { Command } from "./types";
import { legendHistoryReply, type LegendFinish } from "./legend-history";
import { legendSeasonReply, type LegendSeasonSummary, type LegendSeasonDay, type LegendDayDetails } from "./legend-season";
import { globalLegendStats } from "./legend-global";

interface Rank { tag: string; name: string; trophies: number; globalRank: number; location?:{name:string;countryCode?:string} }

export const legendsCommand: Command = {
  deferred:true,
  definition:{name:"legends",description:"Legend League days, clan rankings, history and season stats",type:1,integration_types:[0,1],contexts:[0,1,2],options:[
    {name:"player",description:"Show a player's Legend day, prior days and season graph",type:OptionType.Subcommand,options:[playerOption]},
    {name:"clan",description:"Show a clan's current Legend rankings",type:OptionType.Subcommand,options:[{name:"clan",description:"Clan tag",type:OptionType.String,required:true}]},
    {name:"history",description:"Show a player's Legend season finishes",type:OptionType.Subcommand,options:[
      {...playerOption,required:true,description:"Player tag or one of your bookmarked or verified linked players"},
      {name:"limit",description:"Number of recent season finishes to show (default: all)",type:OptionType.Integer,min_value:1,max_value:240},
    ]},
    {name:"stats",description:"Global Legend rankings, trophy buckets, season winners and daily stats",type:OptionType.Subcommand,options:[
      {name:"type",description:"Global statistic to display",type:OptionType.String,required:true,choices:[
        {name:"Rank Cutoff",value:"cutoffs"},{name:"Trophy Buckets",value:"buckets"},{name:"EOS Finishers",value:"winners"},{name:"Daily Performance",value:"daily"},
      ]},
      {name:"limit",description:"Maximum entries (default 50)",type:OptionType.Integer,min_value:1,max_value:50},
    ]},
  ]},autocomplete:context=>personalPlayerAutocomplete(context,{legendsOnly:subcommand(context).path[0]==="player"}),
  async execute(context){
    const ctx=subcommand(context),emoji=await emojis(ctx),day=legendDay();
    if(ctx.path[0]==="stats")return globalLegendStats(ctx);
    if(["history","player"].includes(ctx.path[0]??"")&&!stringOption(ctx,"player")?.trim())throw new CommandInputError("Choose a player or enter a player tag.");
    if(ctx.path[0]==="clan"){
      const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale);
      const clan=await ctx.services.api.get<{name:string;badgeUrls?:{small?:string};memberList:Array<{tag:string;name:string;trophies:number;leagueTier?:{id?:number;name:string};league?:{id?:number;name:string}}> }>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`);
      const ranks=await ctx.services.api.post<{items:Rank[]}>("/v2/legends/ranks",{tags:clan.memberList.map(member=>member.tag)});
      const rankMap=new Map(ranks.items.map(item=>[item.tag,item]));
      const members=clan.memberList.filter(member=>{
        const league=member.leagueTier??member.league;
        return league?league.id===29000022||((league.id??0)>=105000034&&(league.id??0)<=105000036)||/^Legend(?: League)?(?: |$)/iu.test(league.name):rankMap.has(member.tag);
      }).sort((a,b)=>b.trophies-a.trophies);
      const summaries=await ctx.services.api.post<{items:Array<{tag:string;attacks:number;defenses:number;attackTrophies:number;defenseTrophies:number;netTrophies:number}>}>("/v2/legends/days",{day,tags:members.map(member=>member.tag)});
      const byTag=new Map(summaries.items.map(item=>[item.tag,item]));
      const signed=(value:number)=>`${value>=0?"+":""}${value.toLocaleString("en")}`;
      const entries=members.map(member=>{
        const stats=byTag.get(member.tag),rank=rankMap.get(member.tag)?.globalRank;
        // Isolate mixed-direction names from trophies and the numeric day line.
        const name=`\u2068${escapeMarkdown(member.name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,""))}\u2069`;
        return `\u2066**${emoji.get("Legend League")} ${member.trophies.toLocaleString("en")} | ${name}**\u2069\n-# \u2066${stats?`${emoji.get("clash_sword")} ${signed(stats.attackTrophies)} (${stats.attacks}/8)  ${emoji.get("shield")} ${signed(stats.defenseTrophies)} (${stats.defenses}/8)  · ${signed(stats.netTrophies)} net`:"No recorded day data"}${rank?` · #${rank.toLocaleString("en")}`:""}\u2069`;
      });
      const response=await pagedGameReply(ctx,`${clan.name} · Legend League`,entries,"lc",[tag]);
      for(const embed of (response.data?.embeds??[]) as Array<{author?:{name:string;icon_url?:string};description?:string;footer?:{text:string}}>){
        embed.author={name:clan.name,...(clan.badgeUrls?.small?{icon_url:clan.badgeUrls.small}:{})};
        embed.footer={text:day};
        const url=`https://${ctx.env.APP_ENV==="dev"?"local-app":"app"}.clashk.ing/clan/${encodeURIComponent(tag.slice(1))}?tab=competitive`;
        embed.description=`[Open in ClashKing](${url})\n\n${entries.length?embed.description:"No current Legend players in this clan."}`;
      }
      return response;
    }
    const tag=await resolvePlayerTag(ctx),player=await fetchPlayer(ctx,tag).catch(()=>({name:tag,trophies:undefined})),encoded=encodeURIComponent(tag);
    if(ctx.path[0]==="history"){
      const rawLimit=ctx.options.get("limit")?.value;
      const limit=rawLimit===undefined?undefined:Number(rawLimit);
      if(limit!==undefined&&(!Number.isSafeInteger(limit)||limit<1||limit>240))throw new CommandInputError("Limit must be between 1 and 240 season finishes.");
      const result=await ctx.services.api.get<{items:LegendFinish[]}>(`/v2/player/${encoded}/legend-history`);
      const townHall=emoji.component("townHallLevel" in player?player.townHallLevel:0);
      const finishes=[...result.items].sort((a,b)=>b.season.localeCompare(a.season));
      return legendHistoryReply(ctx,{name:player.name,tag},limit===undefined?finishes:finishes.slice(0,limit),townHall?`https://cdn.discordapp.com/emojis/${townHall.id}.png`:undefined);
    }
    // Discord clients may cache the old name briefly after registration.
    // Both names use the full player view; never revive the sparse old embed.
    if(ctx.path[0]==="player"||ctx.path[0]==="search"){
      const result=await ctx.services.api.get<LegendSeasonSummary>(`/v2/player/${encoded}/legend/season`);
      const selected=String(ctx.options.get("__day")?.value??day);
      // Controls can only select a real day in the current season. Validate
      // again here: persistent component payloads are untrusted input.
      if(!/^\d{4}-\d{2}-\d{2}$/u.test(selected)||!Number.isFinite(Date.parse(selected))||new Date(selected).toISOString().slice(0,10)!==selected||selected<result.seasonStart.slice(0,10)||selected>day)throw new CommandInputError("Choose a day in the current Legend season.");
      const view=ctx.options.get("__view")?.value??"day";
      const [series,details,ranks]=await Promise.all([
        ctx.services.api.get<{items:LegendSeasonDay[]}>(`/v2/player/${encoded}/legend/series`,{"time[after]":result.seasonStart.slice(0,10),"time[before]":day}),
        view==="season"?Promise.resolve(undefined):ctx.services.api.get<LegendDayDetails>(`/v2/player/${encoded}/legend/${selected}/battlelog`),
        ctx.services.api.post<{items:Rank[]}>("/v2/legends/ranks",{tags:[tag]}),
      ]);
      const townHall=emoji.component("townHallLevel" in player?player.townHallLevel:0);
      return legendSeasonReply(ctx,{...player,tag,globalRank:ranks.items[0]?.globalRank,location:ranks.items[0]?.location},result,series.items,townHall?`https://cdn.discordapp.com/emojis/${townHall.id}.png`:undefined,details);
    }
    throw new CommandInputError("Choose player, clan, history, or stats.");
  },
};
