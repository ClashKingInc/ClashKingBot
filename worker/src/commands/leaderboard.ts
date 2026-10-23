import { CommandInputError, invokingUserId, OptionType, requireGuildId, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, gameReply, playerUrl, subcommand } from "./game-common";
import { actionRow, legacyMessage } from "../discord/components";
import type { Command, CommandContext } from "./types";

// Untrusted names can contain RTL overrides as well as ordinary Arabic text.
// Strip explicit controls, then isolate the name so scores/ranks stay LTR.
const isolatedName=(name:string)=>`\u2068${escapeMarkdown(name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,""))}\u2069`;
const count=(value:number)=>value.toLocaleString("en-US");
const row=(rank:number,name:string,tag:string,metric:string,clan?:string)=>
  `\u2066**${metric} | ${isolatedName(name)}**\u2069\n-# \u2066\`#${rank}\` · [${tag}](${playerUrl(tag)})${clan?` · ${isolatedName(clan)}`:""}\u2069`;
async function leaderboardReply(ctx:CommandContext,title:string,rows:string[],kind:string,args:string[],empty:string,season?:string){
  if(!rows.length)return gameReply(ctx,title,empty);
  const pages:string[][]=[[]];
  for(const entry of rows){const last=pages[pages.length-1]!;if(last.length>=20||last.join("\n").length+entry.length+1>3500)pages.push([]);pages[pages.length-1]!.push(entry);}
  const requested=Number(ctx.options.get("__page")?.value??0),page=Number.isSafeInteger(requested)?Math.max(0,Math.min(requested,pages.length-1)):0;
  const response=await gameReply(ctx,title,pages[page]!.join("\n"),undefined,[season,pages.length>1?`${page+1}/${pages.length}`:undefined].filter(Boolean).join(" · "));
  if(pages.length>1){const id=(index:number)=>["ck","page",kind,invokingUserId(ctx),...args,String(index)].join(":");response.data!.components=[actionRow(
    {type:2,style:2,label:"Previous",custom_id:id(page-1),disabled:page===0},
    {type:2,style:2,label:"Next",custom_id:id(page+1),disabled:page===pages.length-1},
  )];}
  return response;
}

export const leaderboardCommand:Command={
  deferred:true,
  definition:{name:"leaderboard",description:"Location rankings and family leaderboards",type:1,integration_types:[0,1],contexts:[0,1,2],options:[
    {name:"location",description:"Official player rankings for a location",type:OptionType.Subcommand,options:[
      {name:"location",description:"Location ID, or global",type:OptionType.String,required:true},
      {name:"village",description:"Village to rank",type:OptionType.String,required:true,choices:[{name:"Home Village",value:"home"},{name:"Builder Base",value:"builder"}]},
      {name:"limit",description:"Players to show (default 200)",type:OptionType.Integer,min_value:1,max_value:200},
    ]},
    {name:"family",description:"This server's tracked family leaderboard",type:OptionType.Subcommand,options:[
      {name:"type",description:"Leaderboard statistic",type:OptionType.String,required:true,choices:[{name:"Donations",value:"donations"},{name:"Legends",value:"legends"},{name:"Clan Games",value:"clan-games"}]},
      {name:"limit",description:"Players to show (1–50)",type:OptionType.Integer,min_value:1,max_value:50},
    ]},
  ]},
  async execute(context){
    const ctx=subcommand(context),emoji=await emojis(ctx),max=ctx.path[0]==="location"?200:50,limit=Number(ctx.options.get("limit")?.value??max);
    if(!Number.isInteger(limit)||limit<1||limit>max)throw new CommandInputError(`Limit must be between 1 and ${max}.`);
    if(ctx.path[0]==="location"){
      const location=stringOption(ctx,"location")?.trim(),village=stringOption(ctx,"village");
      if(!location||!village)throw new CommandInputError("Choose a location and village.");
      if(!/^(global|\d{1,12})$/u.test(location)||!["home","builder"].includes(village))throw new CommandInputError("Choose a valid location ID (or global) and village.");
      const result=await ctx.services.api.get<{items:Array<{name:string;tag:string;rank:number;trophies?:number;builderBaseTrophies?:number;clan?:{name:string}}>}>(`/v2/bot/clash/locations/${encodeURIComponent(location)}/rankings/${village==="builder"?"players-builder-base":"players"}`,{limit});
      const icon=emoji.get(village==="builder"?"versus_trophy":"trophy");
      return leaderboardReply(ctx,`${emoji.get("earth")} ${location==="global"?"Global":`Location ${location}`} Top ${result.items.length} ${village==="builder"?"Builder Base Players":"Players"}`.trim(),result.items.map(item=>row(item.rank,item.name,item.tag,`${icon} ${count(item.builderBaseTrophies??item.trophies??0)}`,item.clan?.name)),"bl",[location,village,String(limit)],"No rankings are available for this location.");
    }
    const guild=requireGuildId(ctx),type=stringOption(ctx,"type");
    if(!type)throw new CommandInputError("Choose a family leaderboard statistic.");
    if(!["donations","legends","clan-games"].includes(type))throw new CommandInputError("Choose Donations, Legends, or Clan Games.");
    const result=await ctx.services.api.get<{items:Array<{rank?:number;player_name:string;player_tag:string;clan_name?:string;donated?:number;received?:number;trophies?:number;clan_games?:number}>;season?:string;total:number}>(`/v2/server/${guild}/leaderboards/${type}`,{limit});
    let empty="No recorded results for this statistic in the linked family clans.";
    if(!result.items.length){
      const clans=await ctx.services.api.get<Array<{tag:string}>>(`/v2/server/${guild}/clans-basic`);
      if(!clans.length){
        const settings=new URL("/dashboard/clans",ctx.env.DASHBOARD_BASE_URL);settings.searchParams.set("guildId",guild);
        return legacyMessage({content:`No family clans are linked to this server. [Open clan settings](${settings.href}) to link them.`,allowed_mentions:{parse:[]}},{ephemeral:true});
      }
    }
    const label=type==="donations"?"Donators":type==="legends"?"Legend Players":"Clan Games Players";
    return leaderboardReply(ctx,`Family Top ${result.items.length||limit} ${label}`,result.items.map((item,index)=>row(item.rank??index+1,item.player_name,item.player_tag,
      type==="donations"?`▲ ${count(item.donated??0)}  ▼ ${count(item.received??0)}`:type==="legends"?`${emoji.get("trophy")} ${count(item.trophies??0)}`:`${emoji.get("clan_games")} ${count(item.clan_games??0)}`,item.clan_name)),"bf",[type,String(limit)],empty,result.season);
  },
};
