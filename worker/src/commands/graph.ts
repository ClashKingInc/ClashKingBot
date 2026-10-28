import { dailyMetrics, graphDaily } from "./graph-daily";
import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { subcommand } from "./game-common";
import type { Command } from "./types";
export const graphMetrics={donated:"Donations",received:"Received troops",clanGames:"Recorded Clan Games points",capitalDonated:"Capital Gold donated"};
type Metric=keyof typeof graphMetrics;
interface Row{tag:string;name:string;value:number|null}
const xml=(value:string)=>value.replace(/[&<>"']/gu,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&apos;"})[c]!);
const text=(x:number,y:number,value:string,size=22,color="#c6d0e0")=>`<text x="${x}" y="${y}" fill="${color}" font-size="${size}" font-family="Blogger Sans">${xml(value)}</text>`;
export const graphCommand:Command={
 deferred:true,
 definition:{name:"graph",description:"Charts of recorded clan statistics",type:1,options:[{name:"month",description:"Compare clan contribution totals in a game season",type:OptionType.Subcommand,options:[
 {name:"attribute",description:"Statistic to compare",type:OptionType.String,required:true,choices:Object.entries(graphMetrics).map(([value,name])=>({name,value}))},
 {name:"season",description:"Game season YYYY-MM (default current)",type:OptionType.String},
 {name:"clans",description:"Space-separated clan tags (default linked family)",type:OptionType.String,max_length:250},
 {name:"limit",description:"Top clans to chart (default 10)",type:OptionType.Integer,min_value:1,max_value:15},
 {name:"sort_order",description:"Order by recorded total",type:OptionType.String,choices:[{name:"Descending",value:"desc"},{name:"Ascending",value:"asc"}]},
 ]}]},
 async execute(context){
  const ctx=subcommand(context),attribute=stringOption(ctx,"attribute")??"",season=stringOption(ctx,"season")??"current",limit=Number(ctx.options.get("limit")?.value??10),order=stringOption(ctx,"sort_order")??"desc",raw=stringOption(ctx,"clans")??"";
  if(ctx.path[0]==="daily")return graphDaily(ctx);
  if(!Object.hasOwn(graphMetrics,attribute)||season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!Number.isInteger(limit)||limit<1||limit>15||!["asc","desc"].includes(order))throw new CommandInputError("Choose valid chart options.");
  if(ctx.path[0]==="over-time")return (await import("./graph-series")).graphSeries(ctx);
  const refs=raw?[...new Set(raw.split(/[\s,]+/u).filter(Boolean).map(tag=>normalizeTag(tag,ctx.locale)))].map(tag=>({tag,name:tag})):await ctx.services.api.get<Array<{tag:string;name:string}>>(`/v2/server/${requireGuildId(ctx)}/clans-basic`);
  if(!refs.length||refs.length>50)throw new CommandInputError("Choose 1–50 clans or configure this server's family.");
  const rows:Row[]=[];let resolved=season,unavailable=0;
  for(let i=0;i<refs.length;i+=5){const batch=refs.slice(i,i+5),results=await Promise.allSettled(batch.map(ref=>ctx.services.api.get<{season:string;truncated:boolean;items:Array<Record<Metric,number>>}>(`/v2/bot/clans/${encodeURIComponent(ref.tag)}/season-stats`,season==="current"?{}:{season})));
   for(const [j,result] of results.entries()){
    const ref=batch[j]!;
    if(result.status==="rejected"||result.value.truncated){unavailable++;rows.push({...ref,value:null});continue;}
    if(resolved!=="current"&&resolved!==result.value.season)throw new CommandInputError("The season changed during this chart. Refresh it.");resolved=result.value.season;
    const sum=result.value.items.reduce((n,item)=>n+item[attribute as Metric],0);
    if(!Number.isSafeInteger(sum)||sum<0){unavailable++;rows.push({...ref,value:null});continue;}
    rows.push({...ref,value:sum});
   }
  }
  const selected=rows.filter((row):row is Row&{value:number}=>row.value!==null).sort((a,b)=>(order==="desc"?-1:1)*(a.value-b.value)||a.tag.localeCompare(b.tag)).slice(0,limit);
  const largest=Math.max(1,...selected.map(row=>row.value)),fmt=(n:number)=>new Intl.NumberFormat("en",{notation:"compact",maximumFractionDigits:1}).format(n);
  const {posterArtwork,renderPosterSvg}=await import("./legend-poster");
  let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100"><rect width="1600" height="1100" fill="#101923"/><rect x="45" y="45" width="1510" height="1010" rx="28" fill="#192634"/><image href="${posterArtwork.logo}" x="1280" y="65" width="230" height="85"/>`;
  svg+=text(90,115,graphMetrics[attribute as Metric],42,"#f6d882")+text(90,165,`${resolved} game season · Recorded clan-attributed totals`,25);
  for(let tick=0;tick<=4;tick++){const x=480+tick*225;svg+=`<path d="M${x} 235V960" stroke="#344454"/>`+text(x-8,215,fmt(largest*tick/4),18);}
  selected.forEach((row,index)=>{const y=245+index*46;svg+=text(90,y+23,row.name.slice(0,28),23,"#f0f3fa")+`<rect x="480" y="${y}" width="${Math.max(2,900*row.value/largest)}" height="28" rx="5" fill="#55c8b0"/>`+text(1400,y+23,fmt(row.value),21,"#f0f3fa");});
  if(!selected.length)svg+=text(400,520,"No complete clan totals available",34);
  svg+=text(90,1013,`${selected.length}/${refs.length} clans shown · ${unavailable} unavailable/incomplete · Zero means no recorded events`,22)+"</svg>";
  const response=legacyMessage({allowed_mentions:{parse:[]},content:`${graphMetrics[attribute as Metric]} · ${resolved}. Historical events stay with their recorded clan; unavailable totals are excluded.\n${selected.map(row=>`${row.name.replace(/[<@`*_~]/gu,"").slice(0,50)}: ${row.value.toLocaleString("en")}`).join(" · ")}`,components:raw?[]:[actionRow({type:2,style:2,label:"Refresh",custom_id:`ck:page:gm:${invokingUserId(ctx)}:${attribute}:${season}:${limit}:${order}:0`})]});
  response.data!.attachments=[];
  response.data!.__files=[{name:"clan-contributions.png",bytes:await renderPosterSvg(svg)}];
  return response;
 },
};

graphCommand.definition.options!.push({name:"over-time",description:"Compare recorded contributions across game seasons",type:OptionType.Subcommand,options:[
 {name:"attribute",description:"Statistic to compare",type:OptionType.String,required:true,choices:Object.entries(graphMetrics).map(([value,name])=>({name,value}))},
 {name:"season",description:"Last game season YYYY-MM (default current)",type:OptionType.String},
 {name:"months",description:"Number of game seasons (default 4)",type:OptionType.Integer,min_value:2,max_value:12},
 {name:"limit",description:"Clans ranked by final-season total (default 5)",type:OptionType.Integer,min_value:1,max_value:10},
 {name:"clans",description:"Space-separated clan tags (default linked family)",type:OptionType.String,max_length:250},
]});

graphCommand.definition.options!.push({name:"daily",description:"Daily observations and gains for clans or a family",type:OptionType.Subcommand,options:[
 {name:"attribute",description:"Statistic to graph",type:OptionType.String,required:true,choices:Object.entries(dailyMetrics).map(([value,name])=>({name,value}))},
 {name:"days",description:"UTC days to show, including today (default 30)",type:OptionType.Integer,min_value:1,max_value:180},
 {name:"limit",description:"Clans ranked by window total (default 5)",type:OptionType.Integer,min_value:1,max_value:10},
 {name:"clans",description:"Space-separated clan tags (default linked family)",type:OptionType.String,max_length:250},
]});
