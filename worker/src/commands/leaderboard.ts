import { CommandInputError, invokingUserId, OptionType, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, gameReply, subcommand } from "./game-common";
import { actionRow, type LegacyEmbed } from "../discord/components";
import { builderLeagues } from "./builder-leagues";
import { compactTableRow, COMPACT_TABLE } from "./display-width";
import type { Command, CommandContext } from "./types";

const row=(rank:number,name:string,score:number,icon:string)=>
  `\u200e\`#${String(rank).padStart(2)}\` ${icon} \`${String(score).padStart(5)}\` ${escapeMarkdown(compactTableRow([{value:name,width:24,isolate:true}],12+COMPACT_TABLE.iconColumns))}`;
async function leaderboardReply(ctx:CommandContext,title:string,rows:string[],kind:string,args:string[],empty:string,season?:string){
  if(!rows.length)return gameReply(ctx,title,empty);
  // Page by entry count; split long pages across embeds rather than losing
  // entries to Discord's 4096-character description limit.
  const pages=Array.from({length:Math.ceil(rows.length/50)},(_,index)=>rows.slice(index*50,index*50+50));
  const requested=Number(ctx.options.get("__page")?.value??0),page=Number.isSafeInteger(requested)?Math.max(0,Math.min(requested,pages.length-1)):0;
  const chunks:string[]=[''];
  for(const entry of pages[page]!){if(chunks.at(-1)!.length+entry.length+1>3900)chunks.push('');chunks[chunks.length-1]+=(chunks.at(-1)?'\n':'')+entry;}
  const footer=season;
  const response=await gameReply(ctx,title,chunks[0]!);
  const base=(response.data!.embeds as LegacyEmbed[])[0]!;
  response.data!.embeds=chunks.map((description,index)=>({color:base.color,...(index===0?{title}:{}),description,...(index===chunks.length-1&&footer?{footer:{text:footer}}:{})}));
  const emoji=await emojis(ctx),id=(index:number)=>["ck","page",kind,invokingUserId(ctx),...args,String(index)].join(":");
  response.data!.components=[actionRow(
    ...(pages.length>1?[
      {type:2 as const,style:2 as const,label:"‹",custom_id:id(page-1),disabled:page===0},
      {type:2 as const,style:2 as const,label:`${page+1} / ${pages.length}`,custom_id:`${id(page)}:indicator`,disabled:true},
      {type:2 as const,style:2 as const,label:"›",custom_id:id(page+1),disabled:page===pages.length-1},
    ]:[]),
    {type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id(page)},
  )];
  return response;
}

const types={
 player:{label:"Players",route:"players",icon:"trophy",clans:false},
 clan:{label:"Clans",route:"clans",icon:"trophy",clans:true},
 bb_player:{label:"Builder Base Players",route:"players-builder-base",icon:"versus_trophy",clans:false},
 bb_clan:{label:"Builder Base Clans",route:"clans-builder-base",icon:"versus_trophy",clans:true},
 capital:{label:"Clan Capital",route:"capitals",icon:"capital_trophy",clans:true},
} as const;
type Board=keyof typeof types;
interface Location {id:number;name:string;isCountry:boolean;countryCode?:string}
let locationsCache:{key:string;expires:number;value:Location[]}|undefined;
async function locations(ctx:CommandContext,type:Board){
 const key=ctx.env.CLASHKING_API_BASE_URL;
 if(!locationsCache||locationsCache.key!==key||locationsCache.expires<Date.now()){
  const data=await ctx.services.api.get<{items:Location[]}>("/v2/bot/clash/locations",{},AbortSignal.timeout(10000));
  locationsCache={key,expires:Date.now()+3600000,value:data.items};
 }
 // International is a clan location, not a selectable player country.
 return locationsCache.value.filter(location=>location.isCountry||types[type].clans&&location.name==="International");
}
export const leaderboardCommand:Command={
 deferred:true,
 definition:{name:"leaderboard",description:"Player and clan location rankings",type:1,integration_types:[0,1],contexts:[0,1,2],options:[
  {name:"location",description:"Official rankings for a location",type:OptionType.Subcommand,options:[
   {name:"type",description:"Leaderboard to display",type:OptionType.String,required:true,choices:Object.entries(types).map(([value,type])=>({name:type.label,value}))},
   {name:"location",description:"Country or Global",type:OptionType.String,required:true,autocomplete:true},
   {name:"limit",description:"Entries to show (default 200)",type:OptionType.Integer,min_value:1,max_value:200},
  ]},
 ]},
 async autocomplete(context){
  const ctx=subcommand(context),type=stringOption(ctx,"type") as Board,query=(stringOption(ctx,"location")??"").trim().toLowerCase();
  if(!type||!Object.hasOwn(types,type))return [];
  return [{name:"Global",value:"global"},...(await locations(ctx,type)).map(location=>({name:location.name,value:String(location.id)}))].filter(location=>!query||location.name.toLowerCase().includes(query)||location.value.includes(query)).sort((a,b)=>Number(b.name.toLowerCase()===query)-Number(a.name.toLowerCase()===query)).slice(0,25);
 },
 async execute(context){
  const ctx=subcommand(context),type=stringOption(ctx,"type") as Board,location=stringOption(ctx,"location")?.trim(),limit=Number(ctx.options.get("limit")?.value??200);
  if(ctx.path[0]!=="location"||!Object.hasOwn(types,type)||!location||!Number.isInteger(limit)||limit<1||limit>200)throw new CommandInputError("Choose a leaderboard type, location and limit from 1 to 200.");
  const selected=location==="global"?undefined:(await locations(ctx,type)).find(item=>String(item.id)===location);
  if(location!=="global"&&!selected)throw new CommandInputError("Choose a location supported by this leaderboard.");
  const board=types[type],emoji=await emojis(ctx);
  const result=await ctx.services.api.get<{items:Array<{name:string;tag:string;rank:number;trophies?:number;builderBaseTrophies?:number;clanPoints?:number;clanBuilderBasePoints?:number;clanCapitalPoints?:number;league?:{name:string};leagueTier?:{name:string};clan?:{name:string}}> }>(`/v2/bot/clash/locations/${encodeURIComponent(location)}/rankings/${board.route}`,{limit});
  const builderTiers=type==="bb_player"?await builderLeagues():[];
  const lines=result.items.map(item=>{
   const score=type==="capital"?item.clanCapitalPoints:type==="bb_clan"?item.clanBuilderBasePoints:type==="clan"?item.clanPoints:type==="bb_player"?item.builderBaseTrophies:item.trophies;
   const builderLeague=builderTiers.find(tier=>(score??0)>=tier.trophy_start)?.name;
   const icon=type==="bb_player"?emoji.get(`builder${builderLeague??""}`):
     type==="player"?emoji.get(item.leagueTier?.name??item.league?.name??"Unranked"):emoji.get(board.icon);
   return row(item.rank,item.name,score??0,icon);
  });
  return leaderboardReply(ctx,`${selected?.name??"Global"} ${board.label}`,lines,"bl",[location,type,String(limit)],"No rankings are available for this location.");
 },
};
