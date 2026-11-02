import { graphTotal } from "./graph-data";
import { displayNameColumn } from "./display-width";
import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const groups={categories:"Categories",overview:"Overview",cwl:"CWL leagues",capital:"Capital leagues",location:"Location"};
export const familyDirectoryOptions=():ApplicationCommandOption[]=>[];
interface Ref{tag:string;name:string;category?:string|null;categoryOrder?:number|null}
interface Clan{members?:number;memberList?:unknown[];clanPoints?:number;clanBuilderBasePoints?:number;clanCapitalPoints?:number;warLeague?:{id?:number;name:string};capitalLeague?:{id?:number;name:string};location?:{name:string;countryCode?:string}}
export async function familyDirectory(ctx:CommandContext){
 const guild=requireGuildId(ctx),type=stringOption(ctx,"type")??"categories";
 if(!Object.hasOwn(groups,type))throw new CommandInputError("Choose a directory type.");
 const refs=await ctx.services.api.get<Ref[]>(`/v2/server/${guild}/clans-basic`),clans=[...new Map(refs.map(ref=>[ref.tag,ref])).values()];
 if(!clans.length)throw new CommandInputError("No family clans are linked to this server.");
 if(clans.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
 const rows:Array<{ref:Ref;clan?:Clan;group:string}>=[];
 for(let offset=0;offset<clans.length;offset+=4)rows.push(...await Promise.all(clans.slice(offset,offset+4).map(async ref=>{
  try{const clan=await ctx.services.api.get<Clan>(`/v2/bot/clash/clans/${encodeURIComponent(ref.tag)}`,{},AbortSignal.timeout(15000));
   const group=type==="categories"?ref.category??"Uncategorized":type==="cwl"?clan.warLeague?.name??"Unranked":type==="capital"?clan.capitalLeague?.name??"Unranked":type==="location"?clan.location?.name??"Not set":"";
   return {ref,clan,group};
  }catch{return {ref,group:"Unavailable"};}
 })));
 rows.sort((a,b)=>(type==="categories"?(a.ref.categoryOrder??Infinity)-(b.ref.categoryOrder??Infinity):type==="cwl"?(b.clan?.warLeague?.id??0)-(a.clan?.warLeague?.id??0):type==="capital"?(b.clan?.capitalLeague?.id??0)-(a.clan?.capitalLeague?.id??0):a.group.localeCompare(b.group))||a.group.localeCompare(b.group)||a.ref.name.localeCompare(b.ref.name));
 const emoji=await emojis(ctx),server=await ctx.services.discordRest.getGuild(guild),pages:string[]=[];
 let description="",lastGroup:string|undefined;
 for(const row of rows){
  const groupIcon=type==="cwl"||type==="capital"?emoji.get(row.group):type==="location"?emoji.get("earth"):"";
  const heading=row.group!==lastGroup&&row.group?`${description?"\n":""}${groupIcon} **${escapeMarkdown(row.group)}**\n`:"";
  const members=row.clan?.members??row.clan?.memberList?.length;
  const league=type==="categories"||type==="overview"?emoji.get(row.clan?.warLeague?.name??"Unranked"):"";
  const line=`${league} **${escapeMarkdown(row.ref.name)}** ${emoji.get("people")} [${members===undefined?"—":members}/50](https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(row.ref.tag)})`;
  if(description.length+heading.length+line.length+1>3700){pages.push(description);description=heading.trimStart()+line;}
  else description+=heading+(heading||!description?"":"\n")+line;
  lastGroup=row.group;
 }
 if(description)pages.push(description);
 const page=Math.min(pages.length-1,Math.max(0,Number(ctx.options.get("__page")?.value??0)));
 const id=(index:number)=>`ck:page:fd:${invokingUserId(ctx)}:clans:${type}:200:asc:current:${index}`;
 const unavailable=rows.filter(row=>!row.clan).length;
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{author:{name:`${server.name} Clans`,...(typeof server.icon==="string"?{icon_url:`https://cdn.discordapp.com/icons/${guild}/${server.icon}.png`}:{})},color:await serverEmbedColor(ctx),description:pages[page],footer:{text:`${rows.reduce((sum,row)=>sum+(row.clan?.members??row.clan?.memberList?.length??0),0)} players | ${clans.length} clans${pages.length>1?` | Page ${page+1}/${pages.length}`:""}${unavailable?` | ${unavailable} unavailable`:""}`}}],components:[
  actionRow({type:3,custom_id:id(0).replace(/:0$/u,":directory-type:0"),placeholder:"Directory type",options:Object.entries(groups).map(([value,label])=>({value,label,default:value===type}))}),
  actionRow(...(pages.length>1?[{type:2 as const,style:2 as const,label:"Previous",disabled:page===0,custom_id:id(Math.max(0,page-1))}]:[]),{type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id(page)},...(pages.length>1?[{type:2 as const,style:2 as const,label:"Next",disabled:page===pages.length-1,custom_id:id(page+1)}]:[])),
 ]});
}

/** Clan totals complement the player summary; keep the chosen season on
 * event data while profile metrics remain explicitly current. */
export async function familyClanSummary(ctx:CommandContext){
 const guild=requireGuildId(ctx),limit=Number(ctx.options.get("limit")?.value??10),season=stringOption(ctx,"season")??"current";
 if(!Number.isInteger(limit)||limit<3||limit>15||season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))throw new CommandInputError("Choose a limit from 3 to 15 and a valid season.");
 const refs=await ctx.services.api.get<Ref[]>(`/v2/server/${guild}/clans-basic`),clans=[...new Map(refs.map(ref=>[ref.tag,ref])).values()];
 if(!clans.length)throw new CommandInputError("No family clans are linked to this server.");
 if(clans.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
 const rows:Array<{name:string;donations?:number;received?:number;loot?:number;activity?:number;trophies?:number;builder?:number;capital?:number}>=[];
 let incomplete=false;const seasons=new Set<string>();
 for(let offset=0;offset<clans.length;offset+=4){
  rows.push(...await Promise.all(clans.slice(offset,offset+4).map(async ref=>{
   const [profile,stats,gold,elixir,dark,activity]=await Promise.allSettled([
    ctx.services.api.get<Clan>(`/v2/bot/clash/clans/${encodeURIComponent(ref.tag)}`,{},AbortSignal.timeout(15000)),
    ctx.services.api.get<{season:string;items:Array<{donated:number;received:number}>;truncated:boolean}>(`/v2/bot/clans/${encodeURIComponent(ref.tag)}/season-stats`,season==="current"?{}:{season},AbortSignal.timeout(15000)),
    ...(["gold","elixir","darkElixir","activity"] as const).map(metric=>graphTotal(ctx,ref.tag,season,metric,AbortSignal.timeout(15000))),
   ]);
   for(const data of [stats,gold,elixir,dark,activity])if(data.status==="fulfilled")seasons.add(data.value.season);
   incomplete ||= [gold,elixir,dark,activity].some(data=>data.status==="rejected"||data.value.value===null)||profile.status==="rejected"||stats.status==="rejected"||(stats.status==="fulfilled"&&stats.value.truncated);
   const loot=[gold,elixir,dark];
   const lootTotal=loot.every(data=>data.status==="fulfilled"&&data.value.value!==null)?loot.reduce((sum,data)=>sum+(data.status==="fulfilled"?data.value.value??0:0),0):undefined;
   return {name:ref.name,loot:lootTotal,activity:activity.status==="fulfilled"?activity.value.value??undefined:undefined,...(profile.status==="fulfilled"?{trophies:profile.value.clanPoints,builder:profile.value.clanBuilderBasePoints,capital:profile.value.clanCapitalPoints}:{}),...(stats.status==="fulfilled"&&!stats.value.truncated?{donations:stats.value.items.reduce((sum,row)=>sum+row.donated,0),received:stats.value.items.reduce((sum,row)=>sum+row.received,0)}:{})};
  })));
 }
 const emoji=await emojis(ctx),server=await ctx.services.discordRest.getGuild(guild),color=await serverEmbedColor(ctx);
 const definitions=[['donations','Donations','up_green_arrow'],['received','Received troops','down_red_arrow'],['loot','Loot','gold'],['activity','Activity','clock'],['trophies','Home Village trophies','trophy'],['builder','Builder Base trophies','versus_trophy'],['capital','Clan Capital trophies','capital_trophy']] as const;
 const sections=definitions.flatMap(([key,label,icon])=>{
  const ranked=rows.filter(row=>typeof row[key]==="number"&&row[key]!>0).sort((a,b)=>b[key]!-a[key]!||a.name.localeCompare(b.name)).slice(0,limit);
  return ranked.length?[`**${emoji.get(icon)} ${label}**\n${ranked.map((row,index)=>`\`${String(index+1).padStart(2)} ${compact(row[key]!).padStart(6)} ${displayNameColumn(row.name,20)}\``).join('\n')}`]:[];
 });
 const descriptions:string[]=[];let text="";
 for(const section of sections){if(text&&text.length+section.length+2>3600){descriptions.push(text);text="";}text+=(text?'\n\n':'')+section;}
 if(text)descriptions.push(text);
 const embeds=descriptions.length?descriptions.map(description=>({description,color})): [{description:"No recorded clan statistics for this season.",color}];
 const result=embeds as import('../discord/components').LegacyEmbed[];
 const author={name:`${server.name} (Clan Summary)`,...(typeof server.icon==="string"?{icon_url:`https://cdn.discordapp.com/icons/${guild}/${server.icon}.png`}:{})};
 for(const embed of result)embed.author=author;
 result[result.length-1]!.footer={text:`${[...seasons].join(", ")||season} | ${clans.length} clans${incomplete?" | Some data unavailable":""}`};
 return legacyMessage({allowed_mentions:{parse:[]},embeds:result,components:[actionRow({type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:`ck:page:fs:${invokingUserId(ctx)}:${season}:${limit}:0`})]});
}
