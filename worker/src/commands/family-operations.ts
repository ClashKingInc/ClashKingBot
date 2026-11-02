import { currentRaidWeekend, loadRaidWeekend, raidMedals } from "./raid-data";
import { actionRow, legacyMessage, type LegacyEmbed } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { loadCurrentWar, warTime, type War } from "./war-data";
import type { ApplicationCommandOption, CommandContext } from "./types";

export const familyOngoingOptions: ApplicationCommandOption[] = [
  {name:"type",description:"Ongoing family activity",type:OptionType.String,required:true,choices:[{name:"Wars",value:"wars"},{name:"Raids",value:"raids"}]},
];
interface ClanRef {tag:string;name:string}
interface Row {name:string;detail:string;inactive?:boolean}
export async function familyOperations(ctx:CommandContext){
  const guild=requireGuildId(ctx),type=stringOption(ctx,"type");
  if(!["wars","raids"].includes(type??""))throw new CommandInputError("Choose Wars or Raids.");
  const refs=await ctx.services.api.get<ClanRef[]>(`/v2/server/${guild}/clans-basic`);
  const clans=[...new Map(refs.map(clan=>[clan.tag,clan])).values()];
  if(!clans.length)throw new CommandInputError("No family clans are linked to this server.");
  if(clans.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
  const emoji=await emojis(ctx),server=await ctx.services.discordRest.getGuild(guild),rows:Row[]=[],warCache=new Map<string,Promise<War[]>>();
  for(let offset=0;offset<clans.length;offset+=4){
    rows.push(...await Promise.all(clans.slice(offset,offset+4).map(async(clan):Promise<Row>=>{
      try{
        if(type==="raids"){
          const raid=await loadRaidWeekend(ctx,clan.tag,currentRaidWeekend());
          if(!raid||raid.state!=="ongoing")return {name:clan.name,detail:"",inactive:true};
          const profile=await ctx.services.api.get<{clanCapital?:{capitalHallLevel?:number}}>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}`);
          const hall=profile.clanCapital?.capitalHallLevel,medals=raidMedals(raid);
          return {name:`${clan.name}${hall?` (CH${hall})`:""}`,detail:`${emoji.get("thick_capital_sword")} ${raid.totalAttacks}/300 | ${emoji.get("people")} ${raid.members?.length??"?"}/50\n${emoji.get("capital_gold")} ${compact(raid.capitalTotalLoot)} | ${emoji.get("raid_medal")} ${medals.estimated?"≈":""}${medals.offense+medals.defense}`};
        }
        const {war,privateLog,cwl}=await loadCurrentWar(ctx,clan.tag,warCache);
        if(!war)return {name:clan.name,detail:privateLog?"Private war log":"",inactive:!privateLog};
        if(war.state==="warEnded")return {name:clan.name,detail:"",inactive:true};
        const own=war.clan.tag===clan.tag?war.clan:war.opponent,other=war.clan.tag===clan.tag?war.opponent:war.clan;
        const capacity=war.teamSize*(war.attacksPerMember??(cwl?1:2));
        const hits=(side:typeof own)=>`${side.members.reduce((n,m)=>n+(m.attacks?.length??0),0)}/${capacity}`;
        const timestamp=warTime(war.state==="preparation"?war.startTime??war.endTime:war.endTime);
        return {name:`${clan.name} vs ${other.name}${cwl?" (CWL)":""}`,detail:`\`${hits(own).padEnd(7)}\`${emoji.get("wood_swords")}\`${hits(other).padStart(7)}\`\n\`${String(own.stars).padEnd(7)}\`${emoji.get("war_star")}\`${String(other.stars).padStart(7)}\`\n\`${`${own.destructionPercentage.toFixed(2)}%`.padEnd(7)}\`${emoji.get("broken_sword")}\`${`${other.destructionPercentage.toFixed(2)}%`.padStart(7)}\`${Number.isFinite(timestamp)?`\n${war.state==="preparation"?"Starting":"Ending"} <t:${Math.floor(timestamp/1000)}:R>`:""}`};
      }catch{return {name:clan.name,detail:"Unavailable (retry later)"};}
    })));
  }
  rows.sort((a,b)=>a.name.localeCompare(b.name));
  const visible=rows.filter(row=>!row.inactive),color=await serverEmbedColor(ctx),pages:string[]=[];let text="";
  for(const row of visible){const line=`**${escapeMarkdown(row.name)}**\n${row.detail}`;if(text.length+line.length+2>3500){pages.push(text);text="";}text+=(text?"\n\n":"")+line;}
  if(text)pages.push(text);
  const page=Math.min(pages.length-1,Math.max(0,Number(ctx.options.get("__page")?.value??0)));
  const embeds:LegacyEmbed[]=[{author:{name:`${server.name} (Current ${type==="raids"?"Raids":"Wars"})`,...(typeof server.icon==="string"?{icon_url:`https://cdn.discordapp.com/icons/${guild}/${server.icon}.png`}:{})},color,description:pages[page]??`No ongoing ${type} in these clans.`,footer:{text:`${visible.length}/${clans.length} clans${pages.length>1?` | Page ${page+1}/${pages.length}`:""}`}}];
  const id=(index:number)=>`ck:page:fo:${invokingUserId(ctx)}:${type}:${index}:0`;
  return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow(...(pages.length>1?[{type:2 as const,style:2 as const,label:"Previous",disabled:page<=0,custom_id:id(page-1)}]:[]),{type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id(Math.max(0,page))},...(pages.length>1?[{type:2 as const,style:2 as const,label:"Next",disabled:page===pages.length-1,custom_id:id(page+1)}]:[]))]});
}
