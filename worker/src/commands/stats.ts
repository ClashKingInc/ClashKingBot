import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, normalizeTag, OptionType, requireGuildId, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, subcommand } from "./game-common";
import { clanCommand } from "./clan";
import { serverEmbedColor } from "./embed-color";
import type { Command } from "./types";
const views={h:"Hit rate",d:"Defense conceded rate",a:"Attack info"};
const warTypes:Record<string,string[]>={a:["random","cwl","friendly"],r:["random"],c:["cwl"],f:["friendly"],b:["random","cwl"]};
interface Row{tag:string;name:string;townhall:number;attempts:number;matching:number;stars:number;destruction:number}
interface Report{start:string;end:string;season:string|null;selectedWars:number;loadedWars:number;truncated:boolean;complete:boolean;items:Row[]}
const clean=(text:string)=>escapeMarkdown(text.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"")).slice(0,55);
export const statsCommand:Command={
 deferred:true,
 definition:{name:"stats",description:"Recorded clan and family statistics",type:1,integration_types:[0,1],contexts:[0,1,2],options:[{name:"war",description:"Completed-war hit rates, defense rates and attack information",type:OptionType.Subcommand,options:[
  {name:"type",description:"Statistic to show",type:OptionType.String,choices:Object.entries(views).map(([value,name])=>({name,value}))},
  {name:"clan",description:"Clan tag or name (default this server's family)",type:OptionType.String,autocomplete:true},
  {name:"war_types",description:"Included wars (default All)",type:OptionType.String,choices:[{name:"All",value:"a"},{name:"Regular War",value:"r"},{name:"CWL",value:"c"},{name:"Friendly",value:"f"},{name:"Regular War & CWL",value:"b"}]},
  {name:"th_filter",description:"all, equal, 18, or 18v18 (own TH versus opponent TH)",type:OptionType.String},
  {name:"star_filter",description:"Count these star outcomes, comma-separated (default 3)",type:OptionType.String},
  {name:"season",description:"Game season YYYY-MM; use one window option",type:OptionType.String},
  {name:"num_days",description:"Look back 1–365 days instead of a season",type:OptionType.Integer,min_value:1,max_value:365},
  {name:"num_wars",description:"Latest 1–1000 matching wars instead of a season",type:OptionType.Integer,min_value:1,max_value:1000},
  {name:"min_attacks",description:"Minimum attacks/defenses in the sample (default 5)",type:OptionType.Integer,min_value:1,max_value:1000},
  {name:"limit",description:"Player rows to show (default 30)",type:OptionType.Integer,min_value:1,max_value:50},
  {name:"sort_by",description:"Sort by (default Selected-star rate)",type:OptionType.String,choices:[{name:"Selected-star rate",value:"r"},{name:"Sample size",value:"n"},{name:"Average stars",value:"s"}]},
  {name:"sort_order",description:"Sort direction (defense defaults Lowest first)",type:OptionType.String,choices:[{name:"Highest first",value:"d"},{name:"Lowest first",value:"a"}]},
 ]}]},
 autocomplete:ctx=>clanCommand.autocomplete!(ctx),
 async execute(context){
  const ctx=subcommand(context),view=stringOption(ctx,"type")??"h",war=stringOption(ctx,"war_types")??"a",th=(stringOption(ctx,"th_filter")??"all").trim().toLowerCase(),rawStars=(stringOption(ctx,"star_filter")??"3").replaceAll(" ",""),limit=Number(ctx.options.get("limit")?.value??30),min=Number(ctx.options.get("min_attacks")?.value??5),sort=stringOption(ctx,"sort_by")??"r",order=stringOption(ctx,"sort_order")??(view==="d"?"a":"d");
  const season=stringOption(ctx,"season"),days=ctx.options.get("num_days")?.value,wars=ctx.options.get("num_wars")?.value;
  if(!Object.hasOwn(views,view)||!warTypes[war]||! /^(?:all|equal|(?:[1-9]|[12][0-9]|30)(?:v(?:[1-9]|[12][0-9]|30))?)$/u.test(th)||! /^[0-3](?:,[0-3])*$/u.test(rawStars)||!Number.isInteger(limit)||limit<1||limit>50||!Number.isInteger(min)||min<1||min>1000||!["r","n","s"].includes(sort)||!["a","d"].includes(order))throw new CommandInputError("Choose valid war-statistics filters.");
  if([season,days,wars].filter(value=>value!==undefined).length>1)throw new CommandInputError("Choose only one of season, num_days or num_wars.");
  const target=stringOption(ctx,"clan")?normalizeTag(stringOption(ctx,"clan")!,ctx.locale):"-";
  const clans=target!=="-"?[{tag:target}]:await ctx.services.api.get<Array<{tag:string}>>(`/v2/server/${requireGuildId(ctx)}/clans-basic`);
  if(!clans.length)throw new CommandInputError("No family clans are linked to this server.");
  const stars=[...new Set(rawStars.split(",").map(Number))].sort();
  const report=await ctx.services.api.post<Report>("/v2/bot/war-statistics",{clans:clans.map(clan=>clan.tag),view:view==="d"?"defense":"attack",warTypes:warTypes[war],thFilter:th,stars,...(season?{season}:{}),...(days!==undefined?{days:Number(days)}:{}),...(wars!==undefined?{warCount:Number(wars)}:{})});
  const value=(row:Row)=>sort==="n"?row.attempts:sort==="s"?row.stars/row.attempts:row.matching/row.attempts;
  const rows=report.items.filter(row=>row.attempts>=min).sort((a,b)=>(order==="d"?-1:1)*(value(a)-value(b))||b.attempts-a.attempts||a.tag.localeCompare(b.tag));
  const emoji=await emojis(ctx);let description="",shown=0;
  if(!report.complete)description=report.truncated?"More than 1,000 wars match. Choose fewer days or num_wars to narrow the report.":"Some selected war archives are unavailable. No leaderboard was calculated; refresh to retry.";
  else for(const [index,row] of rows.slice(0,limit).entries()){
   const detail=view==="a"?`${row.attempts} attacks · ${(row.stars/row.attempts).toFixed(2)}★ · ${(row.destruction/row.attempts).toFixed(1)}%`:`${(100*row.matching/row.attempts).toFixed(1)}% · ${row.matching}/${row.attempts}`;
   const line=`${row.townhall?emoji.get(row.townhall):"❔"} **${index+1}. ${clean(row.name||row.tag)}** · ${detail}`;if(description.length+line.length+1>3300)break;description+=(description?"\n":"")+line;shown++;
  }
  description ||= "No players meet the recorded sample and filters.";
  const period=season?`s${season}`:days!==undefined?`d${days}`:wars!==undefined?`w${wars}`:"s-current";
  const id=["ck","page","ws",invokingUserId(ctx),target,view,war,th,stars.join(""),period,min,limit,sort,order,"0"].join(":");
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:`${target==="-"?"Family":target} · ${views[view as keyof typeof views]}`,description,color:await serverEmbedColor(ctx),footer:{text:`${shown}/${rows.length} players · ${report.loadedWars}/${report.selectedWars} recorded wars · ${report.season??(wars!==undefined?`latest ${wars} wars`:`${days} days`)} · stars ${stars.join(",")} · TH ${th}${view==="d"?" · Lower conceded rate is better":""}`}}],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
 }
};
