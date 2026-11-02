import { actionRow, legacyMessage, type LegacyEmbed } from "../discord/components";
import { invokingUserId, normalizeTag, stringOption, CommandInputError } from "./command-utils";
import { emojis, fetchPlayer, type Player } from "./game-common";
import { displayNameColumn } from "./display-width";
import { serverEmbedColor } from "./embed-color";
import type { CommandContext } from "./types";
const views={last_change:"Last Opt Change",last_war:"Last War",timer:"War Timer"};
interface Observation{tag:string;lastPreferenceChange:string|null;lastWarEnd:string|null;timers:Array<{type:"war"|"cwl";endsAt:string}>}
const age=(value:string|null|undefined,timer=false)=>{if(!value)return "—";const time=Date.parse(value);if(!Number.isFinite(time))return "—";const seconds=timer?Math.max(0,(time-Date.now())/1000):Math.max(0,(Date.now()-time)/1000);return seconds>=86400?`${Math.floor(seconds/86400)}d ${Math.floor(seconds%86400/3600)}h`:seconds>=3600?`${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m`:`${Math.floor(seconds/60)}m`;};
export async function warPreference(ctx:CommandContext){
 const tag=normalizeTag(stringOption(ctx,"clan")??"",ctx.locale),view=stringOption(ctx,"view")??"last_change";
 if(!Object.hasOwn(views,view))throw new CommandInputError("Choose a war preference view.");
 const clan=await ctx.services.api.get<{name:string;badgeUrls?:{small?:string};memberList:Array<{tag:string;name:string;townHallLevel?:number}>}>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`);
 const profiles=new Map<string,Player>();
 for(let i=0;i<clan.memberList.length;i+=10){const batch=clan.memberList.slice(i,i+10),results=await Promise.allSettled(batch.map(member=>fetchPlayer(ctx,member.tag)));for(const [j,result]of results.entries())if(result.status==="fulfilled")profiles.set(batch[j]!.tag,result.value);}
 const result=await ctx.services.api.post<{items:Observation[]}>("/v2/bot/players/war-status",{tags:clan.memberList.map(member=>member.tag)}).catch(()=>undefined);
 const history=new Map(result?.items.map(row=>[row.tag,row])??[]),emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const rows=clan.memberList.map(member=>({member,profile:profiles.get(member.tag)})).sort((a,b)=>(b.profile?.townHallLevel??b.member.townHallLevel??0)-(a.profile?.townHallLevel??a.member.townHallLevel??0)||a.member.name.localeCompare(b.member.name));
 const embeds:LegacyEmbed[]=[];
 for(const state of ["in","out","unknown"]){
  const selected=rows.filter(({profile})=>(profile?.warPreference??"unknown")===state);if(!selected.length)continue;
  const lines=selected.map(({member,profile})=>{const item=history.get(member.tag),value=view==="last_change"?age(item?.lastPreferenceChange):view==="last_war"?age(item?.lastWarEnd):age(item?.timers.filter(t=>Date.parse(t.endsAt)>Date.now()).sort((a,b)=>Date.parse(b.endsAt)-Date.parse(a.endsAt))[0]?.endsAt,true);return `${emoji.get(profile?.townHallLevel??member.townHallLevel??0)}\`${value.padEnd(8)} ${displayNameColumn(member.name,18)}\``;});
  const heading=`**${state==="in"?`${emoji.get("opt_in")} Opted In`:state==="out"?`${emoji.get("opt_out")} Opted Out`:"Preference unavailable"} (${selected.length})**\n\`${views[view as keyof typeof views]} | Name\`\n`;
  let text=heading;for(const line of lines){if(text.length+line.length+1>3800){embeds.push({color,description:text});text=heading;}text+=line+"\n";}embeds.push({color,description:text});
 }
 if(!embeds.length)embeds.push({color,description:"No clan members."});
 embeds[0]!.author={name:`${clan.name} War Preferences`,...(clan.badgeUrls?.small?{icon_url:clan.badgeUrls.small}:{})};
 embeds.at(-1)!.footer={text:result?`${rows.filter(r=>r.profile?.warPreference==="in").length} opted in | ${rows.filter(r=>r.profile?.warPreference==="out").length} opted out`:"History unavailable"};
 // Missing profiles/history stay unknown; never turn an unavailable timer into availability.
 const id=`ck:page:wp:${invokingUserId(ctx)}:${tag}:${view}:all:0`;
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow({type:3,custom_id:`${id}:preference-view:0`,placeholder:views[view as keyof typeof views],options:Object.entries(views).map(([value,label])=>({label,value,default:value===view}))}),actionRow({type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:`${id}:0`})]});
}
