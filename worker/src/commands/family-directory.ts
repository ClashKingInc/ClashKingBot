import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const groups={categories:"Categories",overview:"Overview",cwl:"CWL leagues",capital:"Capital leagues",location:"Location",townhall:"Town Hall requirement"};
const metrics={donations:"Recorded donations",activity:"Active players per observed day",trophies:"Home Village trophies",builder:"Builder Base trophies",capital:"Capital trophies"};
export function familyDirectoryOptions(stats:boolean):ApplicationCommandOption[]{
  return [
    {name:"type",description:stats?"Clan statistic to rank":"How to group the clan directory",type:OptionType.String,required:stats,choices:Object.entries(stats?metrics:groups).map(([value,name])=>({name,value}))},
    {name:"limit",description:"Clans to display (default 30)",type:OptionType.Integer,min_value:1,max_value:50},
    {name:"sort_order",description:stats?"Value order (default Highest first)":"Group/name order (default A to Z)",type:OptionType.String,choices:[{name:stats?"Highest first":"A to Z",value:stats?"desc":"asc"},{name:stats?"Lowest first":"Z to A",value:stats?"asc":"desc"}]},
    ...(stats?[{name:"season",description:"Donation/activity season YYYY-MM (default current)",type:OptionType.String}]:[]),
  ];
}
interface Ref{tag:string;name:string;category?:string|null;categoryOrder?:number|null}
interface Clan{members?:number;memberList?:unknown[];clanPoints?:number;clanBuilderBasePoints?:number;clanCapitalPoints?:number;requiredTownhallLevel?:number;warLeague?:{name:string};capitalLeague?:{name:string};location?:{name:string}}
interface Row{ref:Ref;clan?:Clan;value?:number;group:string;unavailable:boolean}
export async function familyDirectory(ctx:CommandContext){
  const guild=requireGuildId(ctx),stats=ctx.path[0]==="stats",type=stringOption(ctx,"type")??(stats?"donations":"categories"),limit=Number(ctx.options.get("limit")?.value??30),order=stringOption(ctx,"sort_order")??(stats?"desc":"asc"),season=stringOption(ctx,"season")??"current";
  if(!Object.hasOwn(stats?metrics:groups,type)||!Number.isInteger(limit)||limit<1||limit>50||!["asc","desc"].includes(order)||season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))throw new CommandInputError("Choose valid family directory options.");
  const refs=await ctx.services.api.get<Ref[]>(`/v2/server/${guild}/clans-basic`),clans=[...new Map(refs.map(ref=>[ref.tag,ref])).values()];
  if(!clans.length)throw new CommandInputError("No family clans are linked to this server. Add clans in the dashboard first.");
  if(clans.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
  const rows:Row[]=[];
  for(let offset=0;offset<clans.length;offset+=4){
    rows.push(...await Promise.all(clans.slice(offset,offset+4).map(async(ref):Promise<Row>=>{
      try{
        const clan=await ctx.services.api.get<Clan>(`/v2/bot/clash/clans/${encodeURIComponent(ref.tag)}`,{},AbortSignal.timeout(15000));
        let value:number|undefined;
        if(stats&&(type==="donations"||type==="activity")){
          const data=await ctx.services.api.get<{activeDaily:number;items:Array<{donated:number}>;truncated:boolean}>(`/v2/bot/clans/${encodeURIComponent(ref.tag)}/season-stats`,season==="current"?{}:{season},AbortSignal.timeout(15000));
          // A truncated contribution result is not a complete clan total.
          if(data.truncated)return {ref,clan,group:"",unavailable:true};
          value=type==="activity"?data.activeDaily:data.items.reduce((sum,row)=>sum+row.donated,0);
        }else if(stats)value=type==="trophies"?clan.clanPoints:type==="builder"?clan.clanBuilderBasePoints:clan.clanCapitalPoints;
        const group=type==="categories"?ref.category??"Uncategorized":type==="cwl"?clan.warLeague?.name??"Unranked":type==="capital"?clan.capitalLeague?.name??"Unranked":type==="location"?clan.location?.name??"Not set":type==="townhall"?`TH${clan.requiredTownhallLevel??0}`:"All clans";
        return {ref,clan,group,value,unavailable:stats&&!Number.isFinite(value)};
      }catch{return {ref,group:"Unavailable",unavailable:true};}
    })));
  }
  rows.sort((a,b)=>{
    if(stats)return Number(a.unavailable)-Number(b.unavailable)||(order==="desc"?-1:1)*((a.value??0)-(b.value??0))||a.ref.name.localeCompare(b.ref.name);
    const grouping=type==="categories"?(a.ref.categoryOrder??Number.MAX_SAFE_INTEGER)-(b.ref.categoryOrder??Number.MAX_SAFE_INTEGER):type==="townhall"?(a.clan?.requiredTownhallLevel??0)-(b.clan?.requiredTownhallLevel??0):a.group.localeCompare(b.group);
    return (order==="desc"?-1:1)*(grouping||a.ref.name.localeCompare(b.ref.name))||a.ref.tag.localeCompare(b.ref.tag);
  });
  const emoji=await emojis(ctx);let description="",shown=0,lastGroup="";
  for(const row of rows.slice(0,limit)){
    const heading=!stats&&row.group!==lastGroup?`**${escapeMarkdown(row.group)}**\n`:"";
    const members=row.clan?.members??row.clan?.memberList?.length;
    const value=stats?(row.unavailable?"Unavailable":compact(row.value!)):`${members===undefined?"Members unavailable":`${members}/50 members`} · ${escapeMarkdown(row.clan?.warLeague?.name??"Unranked")}`;
    const line=`${heading}${stats?(row.unavailable?"— ":`**#${shown+1}** `):""}${emoji.get(stats?type==="capital"?"capital_trophy":"trophy":"clan")} **${escapeMarkdown(row.ref.name).slice(0,80)}** · ${value}`;
    if(description.length+line.length+2>3700)break;
    description+=(description?"\n\n":"")+line;shown++;lastGroup=row.group;
  }
  const period=stats&&(type==="donations"||type==="activity")?` · ${season==="current"?"Current season":season}`:" · Current clan profiles";
  const id=["ck","page","fd",invokingUserId(ctx),stats?"stats":"clans",type,String(limit),order,season,"0"].join(":");
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{title:stats?`Family · ${metrics[type as keyof typeof metrics]}`:"Family Clans",color:await serverEmbedColor(ctx),description:description||"No clan data available.",footer:{text:`${shown}/${rows.length} clans · ${rows.filter(row=>row.unavailable).length} unavailable${period}`}}],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
