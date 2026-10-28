import { currentReportMembers } from "./report-members";
import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, stringOption } from "./command-utils";
import { emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const categories={heroes:"Heroes & Pets",troops:"Troops, Spells & Siege Machines",equipment:"Hero Equipment",all:"All Units"};
export const upgradeProgressOptions:ApplicationCommandOption[]=[
 {name:"type",description:"Upgrades to report",type:OptionType.String,required:true,choices:Object.entries(categories).map(([value,name])=>({name,value}))},
 {name:"season",description:"Game season YYYY-MM (default current)",type:OptionType.String},
 {name:"limit",description:"Player rows to show (default 30)",type:OptionType.Integer,min_value:1,max_value:50},
 {name:"sort_by",description:"Rank by observed changes or levels gained",type:OptionType.String,choices:[{name:"Observed changes",value:"changes"},{name:"Levels gained",value:"levels"}]},
 {name:"sort_order",description:"Ranking direction",type:OptionType.String,choices:[{name:"Highest first",value:"desc"},{name:"Lowest first",value:"asc"}]},
 {name:"townhall",description:"Filter by current Town Hall",type:OptionType.Integer,min_value:1,max_value:30},
];
interface Unit{type:number;itemId:number;name:string;changes:number;levels:number}
interface Result{season:string;start:string;end:string;items:Array<{tag:string;units:Unit[]}>}
const clean=(name:string)=>escapeMarkdown(name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"")).slice(0,80);
const packed=(lines:string[],max:number)=>{let text="",count=0;for(const line of lines){if(text.length+line.length+1>max)break;text+=(text?"\n":"")+line;count++;}return {text,count};};
export async function upgradeProgress(ctx:CommandContext,scope:"clan"|"family"){
 const type=stringOption(ctx,"type")??"heroes",season=stringOption(ctx,"season")??"current",sort=stringOption(ctx,"sort_by")??"changes",order=stringOption(ctx,"sort_order")??"desc",limit=Number(ctx.options.get("limit")?.value??30),hall=Number(ctx.options.get("townhall")?.value??0);
 if(!Object.hasOwn(categories,type)||season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)||!["changes","levels"].includes(sort)||!["asc","desc"].includes(order)||!Number.isInteger(limit)||limit<1||limit>50||!Number.isInteger(hall)||hall<0||hall>30)throw new CommandInputError("Choose valid upgrade progress options.");
 const {target,clans,members,failedClans}=await currentReportMembers(ctx,scope,hall);let failedPlayers=0;
 const byTag=new Map<string,Unit[]>();let window:Result|undefined;
 // Families can span multiple snapshots. Deduplicate first, then use bounded
 // batches so a member contributes once even when two clans still list them.
 for(let i=0;i<members.length;i+=400){
  const batches=Array.from({length:Math.ceil(Math.min(400,members.length-i)/100)},(_,j)=>members.slice(i+j*100,i+(j+1)*100));
  const results=await Promise.allSettled(batches.map(batch=>ctx.services.api.post<Result>("/v2/bot/players/upgrade-progress",{tags:batch.map(member=>member.tag),type,...(season==="current"?{}:{season})})));
  for(const [index,result] of results.entries())if(result.status==="fulfilled"){
    if(window&&window.season!==result.value.season)throw new CommandInputError("The game season changed while loading. Refresh this report.");
    window=result.value;for(const row of result.value.items)byTag.set(row.tag,row.units);
  }else failedPlayers+=batches[index]!.length;
 }
 const rows=members.flatMap(member=>{const units=byTag.get(member.tag);return units?.length?[{member,units,changes:units.reduce((sum,u)=>sum+u.changes,0),levels:units.reduce((sum,u)=>sum+u.levels,0)}]:[];}).sort((a,b)=>(order==="desc"?-1:1)*(a[sort as "changes"|"levels"]-b[sort as "changes"|"levels"])||a.member.tag.localeCompare(b.member.tag));
 const emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const playerLines=rows.slice(0,limit).map((row,index)=>`**${index+1}. ${clean(row.member.name)}** · ${row.changes} changes · +${row.levels} levels\n-# ${row.units.slice().sort((a,b)=>b[sort as "changes"|"levels"]-a[sort as "changes"|"levels"]).slice(0,3).map(unit=>`${emoji.get(unit.name)} ${clean(unit.name)} +${unit.levels}`).join(" · ")}`);
 const totals=new Map<string,Unit>();for(const row of rows)for(const unit of row.units){const key=`${unit.type}:${unit.itemId}`,old=totals.get(key);totals.set(key,old?{...unit,changes:old.changes+unit.changes,levels:old.levels+unit.levels}:{...unit});}
 const players=packed(playerLines,3300),units=packed([...totals.values()].sort((a,b)=>b.levels-a.levels||a.name.localeCompare(b.name)).map(unit=>`${emoji.get(unit.name)} **${clean(unit.name)}** · ${unit.changes} changes · +${unit.levels} levels`),1800);
 const date=window?`${window.start.slice(0,10)} → ${window.end.slice(0,10)} (end excluded)`:season;
 const id=["ck","page",scope==="clan"?"uc":"up",invokingUserId(ctx),...(scope==="clan"?[target]:[]),type,season,String(limit),order,sort,String(hall),"0"].join(":");
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:`${scope==="clan"?clean(clans[0]?.name??target):"Family"} · ${categories[type as keyof typeof categories]} progress`,color,description:players.text||(failedClans||failedPlayers?"Some member or upgrade history could not be loaded. Refresh to retry.":"No recorded upgrade changes for these members and filters."),footer:{text:`${players.count}/${rows.length} players with changes · ${members.length} current members · ${failedClans} unavailable clans / ${failedPlayers} unavailable players · ${date}`}}, {title:"Recorded unit totals",color,description:units.text||"No observed upgrades.",footer:{text:`${units.count}/${totals.size} units · ${rows.reduce((sum,row)=>sum+row.changes,0)} observed changes · +${rows.reduce((sum,row)=>sum+row.levels,0)} levels`}}],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
