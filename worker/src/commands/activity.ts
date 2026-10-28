import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { compact, escapeMarkdown } from "./game-common";
import { displayNameColumn } from "./display-width";
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
const age=(iso:string|null)=>{if(!iso)return "N/A";const seconds=Math.max(0,(Date.now()-Date.parse(iso))/1000);return seconds<60?"<1m":seconds<3600?`${Math.floor(seconds/60)}m`:seconds<86400?`${Math.floor(seconds/3600)}h`:`${Math.floor(seconds/86400)}d`;};
export async function activityReport(ctx:CommandContext,scope:"clan"|"family"){
 const season=stringOption(ctx,"season")??"current",hall=Number(ctx.options.get("townhall")?.value??0),limit=Number(ctx.options.get("limit")?.value??30),sort=stringOption(ctx,"sort_by")??"activity",order=stringOption(ctx,"sort_order")??"desc";
 if(season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!Number.isInteger(hall)||hall<0||hall>30||!Number.isInteger(limit)||limit<1||limit>50||!["activity","online","name"].includes(sort)||!["asc","desc"].includes(order))throw new CommandInputError("Choose valid activity options.");
 const target=scope==="clan"?normalizeTag(stringOption(ctx,"clan")??"",ctx.locale):requireGuildId(ctx);
 const clans=scope==="clan"?[{tag:target,name:target}]:await ctx.services.api.get<Array<{tag:string;name:string}>>(`/v2/server/${target}/clans-basic`);
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
 let description=data.current?"` #  ACT   LO  TH NAME         `":"` #  ACT  TH NAME         `",shown=0;
 for(const row of rows.slice(0,limit)){
  const line=`\u2066\`${String(shown+1).padStart(2)} ${compact(row.activity).padStart(4)} ${data.current?age(row.lastObservedAt).padStart(4)+" ":""}${String(row.townHallLevel||"?").padStart(2)} \u2068${displayNameColumn(row.name,13)}\u2069\`\u2069`;
  if(description.length+line.length+1>3600)break;description+="\n"+line;shown++;
 }
 if(!shown)description="No recorded activity for this season and filter.";
 const color=await serverEmbedColor(ctx),embeds=[{title:`${scope==="family"?"Family":escapeMarkdown(unique[0]!.name)} activity`,description,color,footer:{text:`${data.season} · ${shown}/${rows.length} players · ${compact(rows.reduce((sum,row)=>sum+row.activity,0))} filtered events · LO = last observed game activity`}}];
 if(scope==="family"){
  let totals="",count=0;
  for(const row of [...data.clanTotals].sort((a,b)=>b.activity-a.activity||a.tag.localeCompare(b.tag))){const line=`**${escapeMarkdown(unique.find(clan=>clan.tag===row.tag)?.name??row.tag).slice(0,80)}** · ${compact(row.activity)}`;if(totals.length+line.length+1>1500)break;totals+=(totals?"\n":"")+line;count++;}
  embeds.push({title:"Clan activity totals",description:totals,color,footer:{text:`${count}/${unique.length} clans · All recorded members, before the Town Hall filter`}});
 }
 const id=["ck","page",scope==="clan"?"ca":"fa",invokingUserId(ctx),...(scope==="clan"?[target]:[]),season,hall,limit,sort,order,"0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
