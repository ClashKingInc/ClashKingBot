import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, fetchPlayer, type Player } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";
const views={last_change:"Last preference change",last_war:"Last recorded completed war",timer:"Recorded active war timers"};
export const warPreferenceOptions:ApplicationCommandOption[]=[
 {name:"view",description:"Which recorded detail to show",type:OptionType.String,choices:Object.entries(views).map(([value,name])=>({name,value}))},
 {name:"status",description:"War preference to show",type:OptionType.String,choices:[{name:"All",value:"all"},{name:"Opted in",value:"in"},{name:"Opted out",value:"out"}]},
 {name:"townhall",description:"Filter by current Town Hall",type:OptionType.Integer,min_value:1,max_value:30},
];
interface Observation{tag:string;lastPreferenceChange:string|null;lastWarEnd:string|null;timers:Array<{type:"war"|"cwl";endsAt:string}>}
const clean=(name:string)=>escapeMarkdown(name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,"")).slice(0,55);
const stamp=(value:string)=>{const time=Date.parse(value);return Number.isFinite(time)?`<t:${Math.floor(time/1000)}:R>`:"Unknown";};
export async function warPreference(ctx:CommandContext){
 const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale),view=stringOption(ctx,"view")??"last_change",status=stringOption(ctx,"status")??"all",hall=Number(ctx.options.get("townhall")?.value??0);
 if(!Object.hasOwn(views,view)||!["all","in","out"].includes(status)||!Number.isInteger(hall)||hall<0||hall>30)throw new CommandInputError("Choose valid war-preference options.");
 const clan=await ctx.services.api.get<{name:string;memberList:Array<{tag:string;name:string;townHallLevel?:number}>}>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`);
 const members=[...new Map(clan.memberList.map(member=>[member.tag,member])).values()].filter(member=>!hall||member.townHallLevel===hall);
 if(members.length>100)throw new CommandInputError("This report supports up to 100 members.");
 const profiles=new Map<string,Player>();let failedProfiles=0;
 for(let i=0;i<members.length;i+=5){const batch=members.slice(i,i+5),results=await Promise.allSettled(batch.map(member=>fetchPlayer(ctx,member.tag)));for(const [index,result] of results.entries())if(result.status==="fulfilled")profiles.set(batch[index]!.tag,result.value);else failedProfiles++;}
 const observation=members.length?await ctx.services.api.post<{items:Observation[]}>("/v2/bot/players/war-status",{tags:members.map(member=>member.tag)}).catch(()=>undefined):{items:[]};
 const history=new Map(observation?.items.map(item=>[item.tag,item])??[]),emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const rows=members.map(member=>{const profile=profiles.get(member.tag);return {member,profile,state:profile?.warPreference==="in"?"in":profile?.warPreference==="out"?"out":"unknown"};}).sort((a,b)=>(b.profile?.townHallLevel??b.member.townHallLevel??0)-(a.profile?.townHallLevel??a.member.townHallLevel??0)||a.member.name.localeCompare(b.member.name));
 const embeds=[];
 for(const group of ["in","out","unknown"]){
  if(status!=="all"&&status!==group)continue;
  const selected=rows.filter(row=>row.state===group);if(group==="unknown"&&!selected.length)continue;
  const lines=selected.map(row=>{const detail=history.get(row.member.tag);let value="History unavailable";
   if(detail){if(view==="last_change")value=detail.lastPreferenceChange?stamp(detail.lastPreferenceChange):"No recorded change";
    else if(view==="last_war")value=detail.lastWarEnd?stamp(detail.lastWarEnd):"No recorded completed war";
    else value=detail.timers.length?detail.timers.map(timer=>`${timer.type==="cwl"?"CWL":"War"} ${stamp(timer.endsAt)}`).join(" · "):"No recorded active timer";}
   return `${emoji.get(row.profile?.townHallLevel??row.member.townHallLevel??1)} **${clean(row.member.name)}** · ${value}`;
  });
  let description="",shown=0;for(const line of lines){if(description.length+line.length+1>1650)break;description+=(description?"\n":"")+line;shown++;}
  const label=group==="in"?"Opted in":group==="out"?"Opted out":"Preference unknown";
  embeds.push({title:`${clean(clan.name)} · ${label} (${selected.length})`,color,description:description||"None for these filters.",footer:{text:`${views[view as keyof typeof views]} · ${shown}/${selected.length} shown${failedProfiles?` · ${failedProfiles} unavailable profiles`:""}${!observation?" · History unavailable":""}`}});
 }
 // Unknown profiles stay unknown, never silently counted as opted out. Stored
 // timers/history are observations; their absence does not establish eligibility.
 return legacyMessage({allowed_mentions:{parse:[]},content:view==="timer"?"Recorded war/CWL timers only. No timer does not prove a player is free to war.":undefined,embeds,components:[actionRow({type:2,style:2,label:"Refresh",custom_id:["ck","page","wp",invokingUserId(ctx),tag,view,status,String(hall),"0"].join(":")})]});
}
