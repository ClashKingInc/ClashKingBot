import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { loadCurrentWar, warTime, type War } from "./war-data";
import type { ApplicationCommandOption, CommandContext } from "./types";

export const familyOperationOptions: ApplicationCommandOption[] = [
  {name:"limit",description:"Clan rows to show (default 30)",type:OptionType.Integer,min_value:1,max_value:50},
  {name:"sort_order",description:"Clan name order",type:OptionType.String,choices:[{name:"A to Z",value:"asc"},{name:"Z to A",value:"desc"}]},
];
export const familyRaidOptions: ApplicationCommandOption[] = [
  ...familyOperationOptions,
  {name:"weekend",description:"Raid weekend start date YYYY-MM-DD (default most recent Friday)",type:OptionType.String},
];
export const familyWarOptions: ApplicationCommandOption[] = [
  ...familyOperationOptions,
  {name:"include_ended",description:"Include the most recently returned ended war (default false)",type:OptionType.Boolean},
];
interface ClanRef {tag:string;name:string}
interface Raid {
  state:string;startTime:string;endTime:string;totalAttacks:number;capitalTotalLoot:number;
  raidsCompleted:number;enemyDistrictsDestroyed:number;
  members?: Array<{tag:string}>;
}
interface Row {clan:ClanRef;detail?:string;status:"shown"|"inactive"|"private"|"unavailable"}
function currentWeekend(){
  const now=new Date(),friday=new Date(now);
  friday.setUTCDate(now.getUTCDate()-(now.getUTCDay()+2)%7);friday.setUTCHours(7,0,0,0);
  if(friday>now)friday.setUTCDate(friday.getUTCDate()-7);
  return friday.toISOString().slice(0,10);
}
export async function familyOperations(ctx:CommandContext){
  const guild=requireGuildId(ctx),action=ctx.path[0];
  const limit=Number(ctx.options.get("limit")?.value??30),order=stringOption(ctx,"sort_order")??"asc";
  const explicitWeekend=stringOption(ctx,"weekend"),weekend=explicitWeekend??currentWeekend();
  const includeEnded=ctx.options.get("include_ended")?.value===true;
  if(!["wars","raids"].includes(action??"")||!Number.isInteger(limit)||limit<1||limit>50||!["asc","desc"].includes(order))throw new CommandInputError("Choose valid family report options.");
  if(action==="raids"&&(!/^\d{4}-\d{2}-\d{2}$/u.test(weekend)||!Number.isFinite(Date.parse(weekend))||new Date(weekend).toISOString().slice(0,10)!==weekend||new Date(weekend).getUTCDay()!==5||weekend>currentWeekend()))throw new CommandInputError("Choose a Friday on or before the most recent raid weekend.");
  const refs=await ctx.services.api.get<ClanRef[]>(`/v2/server/${guild}/clans-basic`);
  const clans=[...new Map(refs.map(clan=>[clan.tag,clan])).values()];
  if(!clans.length)throw new CommandInputError("No family clans are linked to this server. Add clans in the dashboard first.");
  if(clans.length>200)throw new CommandInputError("This report supports up to 200 linked clans.");
  const emoji=await emojis(ctx),rows:Row[]=[],warCache=new Map<string,Promise<War[]>>();
  for(let offset=0;offset<clans.length;offset+=4){
    rows.push(...await Promise.all(clans.slice(offset,offset+4).map(async(clan):Promise<Row>=>{
      try{
        if(action==="raids"){
          const result=await ctx.services.api.get<{items:Raid[]}>(`/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}/capitalraidseasons`,{limit:10},AbortSignal.timeout(15000));
          // A clan may skip weekends. Never relabel its previous raid as the
          // requested Friday, even if that is the first returned API entry.
          const raid=result.items.find(item=>{const time=warTime(item.startTime);return Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===weekend;});
          if(!raid)return {clan,status:"inactive"};
          return {clan,status:"shown",detail:`${raid.state==="ongoing"?"Ongoing":"Ended"} · ${raid.totalAttacks} attacks · ${raid.members?`${raid.members.length} participants`:"Participants unavailable"}\n${emoji.get("capital_gold")} ${compact(raid.capitalTotalLoot)} looted · ${raid.enemyDistrictsDestroyed} districts · ${raid.raidsCompleted} raids completed`};
        }
        const {war,privateLog,cwl}=await loadCurrentWar(ctx,clan.tag,warCache);
        if(!war)return {clan,status:privateLog?"private":"inactive"};
        if(war.state==="warEnded"&&!includeEnded)return {clan,status:"inactive"};
        const own=war.clan.tag===clan.tag?war.clan:war.opponent,opponent=war.clan.tag===clan.tag?war.opponent:war.clan;
        const used=own.members.reduce((sum,member)=>sum+(member.attacks?.length??0),0);
        const capacity=war.teamSize*(war.attacksPerMember??(cwl?1:2));
        const timestamp=warTime(war.state==="preparation"?war.startTime??war.endTime:war.endTime);
        const label=war.state==="preparation"?"Starts":war.state==="warEnded"?"Ended":"Ends";
        return {clan,status:"shown",detail:`${cwl?"CWL · ":""}${war.state==="preparation"?"Preparation":war.state==="warEnded"?"Ended":"In war"} vs ${escapeMarkdown(opponent.name).slice(0,80)}\n${emoji.get("star")} ${own.stars}–${opponent.stars} · ${used}/${capacity} attacks${Number.isFinite(timestamp)?` · ${label} <t:${Math.floor(timestamp/1000)}:R>`:""}`};
      }catch{return {clan,status:"unavailable"};}
    })));
  }
  rows.sort((a,b)=>(order==="asc"?1:-1)*a.clan.name.localeCompare(b.clan.name)||a.clan.tag.localeCompare(b.clan.tag));
  const visible=rows.filter(row=>row.status==="shown"||row.status==="unavailable"||row.status==="private");
  let description="",shown=0;
  for(const row of visible.slice(0,limit)){
    const detail=row.detail??(row.status==="private"?"Private war log · no matching war available":"Unavailable · retry later");
    const line=`**${escapeMarkdown(row.clan.name).slice(0,80)}**\n${detail}`;
    if(description.length+line.length+2>3700)break;
    description+=(description?"\n\n":"")+line;shown++;
  }
  const inactive=rows.filter(row=>row.status==="inactive").length;
  const id=["ck","page","fo",invokingUserId(ctx),action,String(limit),order,action==="raids"?explicitWeekend??"current":includeEnded?"yes":"no","0"].join(":");
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{
    title:action==="raids"?`Family Raids · ${weekend}`:"Family Wars",color:await serverEmbedColor(ctx),
    description:description||(action==="raids"?"No matching raid returned for this weekend.":"No active wars returned for these clans."),
    footer:{text:`${shown}/${visible.length} report rows · ${clans.length} linked clans · ${inactive} ${action==="raids"?"without a matching recent raid":"without an included war"}${action==="raids"?" · Latest 10 API weekends checked":""}`},
  }],components:[actionRow({type:2,style:2,label:"Refresh",custom_id:id})]});
}
