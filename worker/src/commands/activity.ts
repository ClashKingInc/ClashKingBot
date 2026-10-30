import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";

interface Activity {season:string;current:boolean;truncated:boolean;items:Array<{tag:string;name:string;townHallLevel:number;activity:number;lastObservedAt:string|null}>;clanTotals:Array<{tag:string;activity:number}>}
export const activityOptions:ApplicationCommandOption[]=[
 {name:"season",description:"Game season YYYY-MM (default current)",type:OptionType.String},
 {name:"townhall",description:"Only show this Town Hall",type:OptionType.Integer,min_value:1,max_value:30},
 {name:"limit",description:"Top players (default 30; maximum 50)",type:OptionType.Integer,min_value:1,max_value:50},
 {name:"sort_by",description:"Rank by (default Activity)",type:OptionType.String,choices:[{name:"Activity",value:"activity"},{name:"Last online",value:"online"},{name:"Name",value:"name"}]},
 {name:"sort_order",description:"Order (default Highest / latest first)",type:OptionType.String,choices:[{name:"Highest / latest first",value:"desc"},{name:"Lowest / oldest first",value:"asc"}]},
];
export async function activityReport(ctx:CommandContext,scope:"clan"|"family"){
 const season=stringOption(ctx,"season")??"current",hall=Number(ctx.options.get("townhall")?.value??0),limit=Number(ctx.options.get("limit")?.value??30),sort=stringOption(ctx,"sort_by")??"activity",order=stringOption(ctx,"sort_order")??"desc";
 if(season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!Number.isInteger(hall)||hall<0||hall>30||!Number.isInteger(limit)||limit<1||limit>50||!["activity","online","name"].includes(sort)||!["asc","desc"].includes(order))throw new CommandInputError("Choose valid activity options.");
 const target=scope==="clan"?normalizeTag(stringOption(ctx,"clan")??"",ctx.locale):requireGuildId(ctx);
 const clans=scope==="clan"?[{tag:target,...await ctx.services.api.get<{name:string}>(`/v2/bot/clash/clans/${encodeURIComponent(target)}`).catch(()=>({name:target}))}]:await ctx.services.api.get<Array<{tag:string;name:string}>>(`/v2/server/${target}/clans-basic`);
 const unique=[...new Map(clans.map(clan=>[clan.tag,clan])).values()];
 if(!unique.length)throw new CommandInputError("No family clans are linked to this server.");
 if(unique.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
 const data=await ctx.services.api.post<Activity>("/v2/bot/clans/activity",{clanTags:unique.map(clan=>clan.tag),...(season==="current"?{}:{season})});
 // Never rank a truncated prefix as the true leaders. Current last-online data
 // must not leak into a past season or turn missing observations into zero age.
 if(data.truncated)throw new CommandInputError("Too many recorded players for this report. Choose one clan instead.");
 if(sort==="online"&&!data.current)throw new CommandInputError("Last online is available for the current season. Choose Activity or Name for past seasons.");
 const rows=data.items.filter(row=>!hall||row.townHallLevel===hall);
 rows.sort((a,b)=>{
  if(sort==="online"&&(!a.lastObservedAt||!b.lastObservedAt))return Number(!a.lastObservedAt)-Number(!b.lastObservedAt)||a.tag.localeCompare(b.tag);
  const compare=sort==="name"?a.name.localeCompare(b.name):sort==="online"?Date.parse(a.lastObservedAt!)-Date.parse(b.lastObservedAt!):a.activity-b.activity;
  return (order==="asc"?compare:-compare)||a.tag.localeCompare(b.tag);
 });
 const icons=await emojis(ctx);
 let description="",shown=0;
 for(const row of rows.slice(0,limit)){
  const name=escapeMarkdown(row.name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,""));
  const online=data.current?`\n-# ${row.lastObservedAt?`Last online <t:${Math.floor(Date.parse(row.lastObservedAt)/1000)}:R>`:"Last online unknown"}`:"";
  const line=`**${shown+1}.** ${icons.get(row.townHallLevel)} \u2068${name}\u2069 · **${compact(row.activity)}**${online}`;
  if(description.length+line.length+2>3500)break;description+=(description?"\n\n":"")+line;shown++;
 }
 if(!shown)description="No recorded activity for this season and filter.";
 const color=await serverEmbedColor(ctx),embeds=[{title:`${scope==="family"?"Family":escapeMarkdown(unique[0]!.name)} activity`,description,color,footer:{text:`${data.season} · ${shown}/${rows.length} players`}}];
 if(scope==="family"){
  let totals="",count=0;
  for(const row of [...data.clanTotals].sort((a,b)=>b.activity-a.activity||a.tag.localeCompare(b.tag))){const line=`**${escapeMarkdown(unique.find(clan=>clan.tag===row.tag)?.name??row.tag).slice(0,80)}** · ${compact(row.activity)}`;if(totals.length+line.length+1>1500)break;totals+=(totals?"\n":"")+line;count++;}
  embeds.push({title:"Clan activity totals",description:totals,color,footer:{text:`${count}/${unique.length} clans${hall?" · All Town Halls":""}`}});
 }
 const id=["ck","page",scope==="clan"?"ca":"fa",invokingUserId(ctx),...(scope==="clan"?[target]:[]),season,hall,limit,sort,order,"0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
