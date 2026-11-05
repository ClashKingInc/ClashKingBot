import { actionRow, legacyMessage, type LegacyEmbed } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { compact, emojis, playerUrl } from "./game-common";
import { displayNameColumn } from "./display-width";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";

interface Activity {season:string;current:boolean;truncated:boolean;items:Array<{tag:string;name:string;townHallLevel:number;activity:number;lastObservedAt:string|null}>;clanTotals:Array<{tag:string;activity:number}>}
export const activityOptions:ApplicationCommandOption[]=[
 {name:"season",description:"Game season YYYY-MM (default current)",type:OptionType.String},
 {name:"limit",description:"Top players (default 50; maximum 50)",type:OptionType.Integer,min_value:1,max_value:50},
 {name:"sort_by",description:"Rank by (default Activity)",type:OptionType.String,choices:[{name:"Activity",value:"activity"},{name:"Last online",value:"online"},{name:"Name",value:"name"}]},
 {name:"sort_order",description:"Order (default Highest / latest first)",type:OptionType.String,choices:[{name:"Highest / latest first",value:"desc"},{name:"Lowest / oldest first",value:"asc"}]},
];
export const clanActivityOptions=activityOptions;
export async function activityReport(ctx:CommandContext,scope:"clan"|"family"){
 const season=stringOption(ctx,"season")??"current",hall=scope==="clan"?0:0,limit=Number(ctx.options.get("limit")?.value??50),sort=stringOption(ctx,"sort_by")??"activity",order=stringOption(ctx,"sort_order")??"desc";
 if(season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!Number.isInteger(hall)||hall<0||hall>30||!Number.isInteger(limit)||limit<1||limit>50||!["activity","online","name"].includes(sort)||!["asc","desc"].includes(order))throw new CommandInputError("Choose valid activity options.");
 const target=scope==="clan"?normalizeTag(stringOption(ctx,"clan")??"",ctx.locale):requireGuildId(ctx);
 const clans=scope==="clan"?[{tag:target,...await ctx.services.api.get<{name:string;badgeUrls?:{small?:string};memberList?:Array<{tag:string;name:string;townHallLevel?:number}>}>(`/v2/bot/clash/clans/${encodeURIComponent(target)}`)}]:await ctx.services.api.get<Array<{tag:string;name:string}>>(`/v2/server/${target}/clans-basic`);
 const unique=[...new Map(clans.map(clan=>[clan.tag,clan])).values()];
 if(!unique.length)throw new CommandInputError("No family clans are linked to this server.");
 if(unique.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
 const data=await ctx.services.api.post<Activity>("/v2/bot/clans/activity",{clanTags:unique.map(clan=>clan.tag),...(season==="current"?{}:{season})});
 // Never rank a truncated prefix as the true leaders. Current last-online data
 // must not leak into a past season or turn missing observations into zero age.
 if(data.truncated)throw new CommandInputError("Too many recorded players for this report. Choose one clan instead.");
 if(sort==="online"&&!data.current)throw new CommandInputError("Last online is available for the current season. Choose Activity or Name for past seasons.");
 // Clan activity is a current roster report, including members with zero events.
 const roster=(clans[0] as {memberList?:Array<{tag:string;name:string;townHallLevel?:number}>}).memberList;
 if(scope==="clan"&&!roster)throw new CommandInputError("Could not load the clan roster. Please try again.");
 const activityByTag=new Map(data.items.map(row=>[row.tag,row]));
 const rows=scope==="clan"?roster!.map(member=>({...activityByTag.get(member.tag),tag:member.tag,name:member.name,townHallLevel:member.townHallLevel??activityByTag.get(member.tag)?.townHallLevel??0,activity:activityByTag.get(member.tag)?.activity??0,lastObservedAt:activityByTag.get(member.tag)?.lastObservedAt??null})):data.items.filter(row=>!hall||row.townHallLevel===hall);
 rows.sort((a,b)=>{
  if(sort==="online"&&(!a.lastObservedAt||!b.lastObservedAt))return Number(!a.lastObservedAt)-Number(!b.lastObservedAt)||a.tag.localeCompare(b.tag);
  const compare=sort==="name"?a.name.localeCompare(b.name):sort==="online"?Date.parse(a.lastObservedAt!)-Date.parse(b.lastObservedAt!):a.activity-b.activity;
  return (order==="asc"?compare:-compare)||a.tag.localeCompare(b.tag);
 });
 const icons=await emojis(ctx);
 const selected=rows.slice(0,limit), activityWidth=Math.max(3,...selected.map(row=>String(row.activity).length));
 const since=(value:string|null)=>{
  const timestamp=value?Date.parse(value):NaN;
  if(!Number.isFinite(timestamp))return "N/A";
  const minutes=Math.max(0,Math.floor((Date.now()-timestamp)/60000));
  return minutes>=1440?`${Math.floor(minutes/1440)}d`:minutes>=60?`${Math.floor(minutes/60)}h`:`${minutes}m`;
 };
 const superDigits="⁰¹²³⁴⁵⁶⁷⁸⁹";
 const descriptions:string[]=[];
 let description=`\` # ${"ACT".padStart(activityWidth)}${data.current?"   LO   ":" "} NAME         \`\n`,shown=0;
 for(const row of selected){
  // A fixed-width row keeps activity/last-online scannable on mobile. The
  // superscript Town Hall remains the player link, as in the original bot.
  const hall=String(row.townHallLevel).split("").map(digit=>superDigits[Number(digit)]??digit).join("");
  const line=`\`${String(shown+1).padStart(2)} ${String(row.activity).padStart(activityWidth)}${data.current?` ${since(row.lastObservedAt).padStart(6)} `:" "} ${displayNameColumn(row.name,13)}\`[${hall}](${playerUrl(row.tag)})\n`;
  if(description.length+line.length>3900){descriptions.push(description);description="";}description+=line;shown++;
 }
 if(!shown)description="No recorded activity for this season and filter.";
 descriptions.push(description);
 const total=rows.reduce((sum,row)=>sum+row.activity,0);
 const color=await serverEmbedColor(ctx),first=unique[0] as {name:string;badgeUrls?:{small?:string}};
 const guild=scope==="family"?await ctx.services.discordRest.getGuild(target):undefined;
 const icon=typeof guild?.icon==="string"?`https://cdn.discordapp.com/icons/${target}/${guild.icon}.png`:scope==="clan"?first.badgeUrls?.small:undefined;
 const embeds:LegacyEmbed[]=descriptions.map((description,index)=>({...index===0?{author:{name:`${scope==="family"?guild!.name:first.name} Activity${scope==="family"?` (Top ${shown})`:""}`, ...(icon?{icon_url:icon}:{})}}:{},description,color,
  ...(index===descriptions.length-1?{footer:{text:`Total activity: ${total.toLocaleString("en")} (${data.season})${shown<rows.length?` — ${shown}/${rows.length} players`:""}`}}:{})}));
 if(scope==="family"){
  let totals="";
  for(const row of [...data.clanTotals].sort((a,b)=>b.activity-a.activity||a.tag.localeCompare(b.tag))){const line=`\`${compact(row.activity).padStart(7)} ${displayNameColumn(unique.find(clan=>clan.tag===row.tag)?.name??row.tag,20)}\``;if(totals.length+line.length+1>1500)break;totals+=(totals?"\n":"")+line;}
  for(const embed of embeds)delete embed.footer;
  embeds.push({author:{name:`${guild!.name} Clans`,...(icon?{icon_url:icon}:{})},description:totals,color,footer:{text:`Total activity: ${total.toLocaleString("en")} (${data.season}) | ${shown}/${rows.length} players`}});
 }
 const id=["ck","page",scope==="clan"?"ca":"fa",invokingUserId(ctx),...(scope==="clan"?[target]:[]),season,...(scope==="clan"?[limit]:[hall,limit]),sort,order,"0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:2,style:2,emoji:icons.component("refresh")??{name:"↻"},custom_id:id})]});
}
