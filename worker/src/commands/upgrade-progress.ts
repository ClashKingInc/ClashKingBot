import { displayNameColumn } from "./display-width";
import { currentReportMembers } from "./report-members";
import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, stringOption } from "./command-utils";
import { emojis } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const categories={heroes:"Heroes & Pets",troops:"Troops, Spells & Siege Machines",equipment:"Hero Equipment",all:"All Units"};
export const upgradeProgressOptions:ApplicationCommandOption[]=[
 {name:"season",description:"Game season YYYY-MM (defaults to last 30 days)",type:OptionType.String},
];
interface Unit{type:number;itemId:number;name:string;changes:number;levels:number}
interface Result{season:string;start:string;end:string;items:Array<{tag:string;units:Unit[]}>}
const packed=(lines:string[],max:number)=>{let text="",count=0;for(const line of lines){if(text.length+line.length+1>max)break;text+=(text?"\n":"")+line;count++;}return {text,count};};
export async function upgradeProgress(ctx:CommandContext,scope:"clan"|"family"){
 const type=stringOption(ctx,"type")??"all",season=stringOption(ctx,"season")??"last30days",sort="levels",order="desc",limit=50,hall=0;
 if(!Object.hasOwn(categories,type)||!["current","last30days"].includes(season)&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!["changes","levels"].includes(sort)||!["asc","desc"].includes(order)||!Number.isInteger(limit)||limit<1||limit>50||!Number.isInteger(hall)||hall<0||hall>30)throw new CommandInputError("Choose valid upgrade progress options.");
 const {target,clans,members,failedClans}=await currentReportMembers(ctx,scope,hall);let failedPlayers=0;
 const byTag=new Map<string,Unit[]>();let window:Result|undefined;
 // Families can span multiple snapshots. Deduplicate first, then use bounded
 // batches so a member contributes once even when two clans still list them.
 for(let i=0;i<members.length;i+=400){
  const batches=Array.from({length:Math.ceil(Math.min(400,members.length-i)/100)},(_,j)=>members.slice(i+j*100,i+(j+1)*100));
  const results=await Promise.allSettled(batches.map(batch=>ctx.services.api.post<Result>("/v2/bot/players/upgrade-progress",{tags:batch.map(member=>member.tag),type,...(season==="last30days"?{days:30}:season==="current"?{}:{season})})));
  for(const [index,result] of results.entries())if(result.status==="fulfilled"){
    if(window&&window.season!==result.value.season)throw new CommandInputError("The game season changed while loading. Refresh this report.");
    window=result.value;for(const row of result.value.items)byTag.set(row.tag,row.units);
  }else failedPlayers+=batches[index]!.length;
 }
 const rows=members.flatMap(member=>{const units=byTag.get(member.tag);return units?.length?[{member,units,changes:units.reduce((sum,u)=>sum+u.changes,0),levels:units.reduce((sum,u)=>sum+u.levels,0)}]:[];}).sort((a,b)=>(order==="desc"?-1:1)*(a[sort as "changes"|"levels"]-b[sort as "changes"|"levels"])||a.member.tag.localeCompare(b.member.tag));
 const emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const playerLines=rows.slice(0,limit).map((row,index)=>`\`${String(index+1).padStart(2)} ${String(row.levels).padStart(3)} ${displayNameColumn(row.member.name,19)}\``);
 const totals=new Map<string,Unit>();for(const row of rows)for(const unit of row.units){const key=`${unit.type}:${unit.itemId}`,old=totals.get(key);totals.set(key,old?{...unit,changes:old.changes+unit.changes,levels:old.levels+unit.levels}:{...unit});}
 const players=packed(playerLines,3300),units=packed([...totals.values()].sort((a,b)=>b.levels-a.levels||a.name.localeCompare(b.name)).slice(0,15).map(unit=>`${emoji.get(unit.name)} \`${String(unit.levels).padStart(3)} ${displayNameColumn(unit.name,22)}\``),1800);
 const date=season==="last30days"?"Last 30 days":`Season ${window?.season??season}`;
 const id=["ck","page",scope==="clan"?"uc":"up",invokingUserId(ctx),...(scope==="clan"?[target]:[]),type,season,String(limit),order,sort,String(hall),"0"].join(":");
 const clanName=scope==="clan"?clans[0]?.name??target:"Family";
 const guild=scope==="family"?await ctx.services.discordRest.getGuild(target):undefined;
 const author={name:guild?`${guild.name} Upgrades (Top ${players.count})`:clanName,...(typeof guild?.icon==="string"?{icon_url:`https://cdn.discordapp.com/icons/${target}/${guild.icon}.png`}:{}),...(scope==="clan"&&clans[0]?.badgeUrls?.small?{icon_url:clans[0].badgeUrls.small}:{})};
 const typeIcons:Record<string,string>={heroes:"Barbarian King",troops:"Barbarian",equipment:"Giant Gauntlet",all:"clash_sword"};
 const typePicker=actionRow({type:3,custom_id:id.replace(/:0$/u,":progress-type:0"),placeholder:"Upgrade type",options:Object.entries(categories).map(([value,label])=>{
  const icon=emoji.component(typeIcons[value]!);
  return {label,value,default:value===type,...(icon?{emoji:icon}:{})};
 })});
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{
  author,color,
  description:players.text?`\` # UPG Name\`\n${players.text}`:(failedClans||failedPlayers?"Some member or upgrade history could not be loaded. Refresh to retry.":"No recorded upgrade changes for these members."),
 },{
  author:scope==="clan"?{name:"Upgrades by unit (Top 15)"}:{...author,name:`${guild!.name} Units (Top 15)`},color,
  description:units.text||"No observed upgrades.",
  footer:{text:`${date} | ${players.count}/${rows.length} players | ${units.count<totals.size?`Top ${units.count} of ${totals.size}`:units.count} units${failedClans||failedPlayers?" | Some members unavailable":""}`}
 }],components:[typePicker,actionRow({type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id})]});
}
