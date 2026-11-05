import { escapeLinkLabel } from "./game-common";
import { actionRow, legacyMessage, linkButton, type LegacyEmbed } from '../discord/components';
import { emojis, escapeMarkdown } from './game-common';
import { isolatedNameColumn as displayNameColumn } from './display-width';
import { serverEmbedColor } from './embed-color';
import { warTime, type War, type WarSide } from './war-data';
import type { CommandContext } from './types';
export const warViews=[['overview','War Overview','hashmark'],['roster','Clan Roster','troop'],['opponent','Opponent Roster','troop'],['attacks','Attacks','clash_sword'],['defenses','Defenses','shield'],['odefenses','Opponent Defenses','clan_castle'],['opp_over','Opponent Clan Overview','search']] as const;
export async function warSearchView(ctx:CommandContext,tag:string,war:War,cwl:boolean,period:string,view:string,page=0){
 const own=war.clan.tag===tag?war.clan:war.opponent,other=own===war.clan?war.opponent:war.clan,emoji=await emojis(ctx),color=await serverEmbedColor(ctx);
 const clanUrl=(tag:string)=>`https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(tag)}`;
 const title=warViews.find(v=>v[0]===view)?.[1]??'War Overview';
 const embed:LegacyEmbed={author:{name:own.name,...(own.badgeUrls?.small?{icon_url:own.badgeUrls.small}:{})},color,footer:{text:`${cwl?'CWL':'Regular'} War (${war.teamSize} vs ${war.teamSize})`}};
 let pages:string[]=[];
 if(view==='overview'){
  const count=(side:WarSide)=>side.members.reduce((sum,m)=>sum+(m.attacks?.length??0),0),max=war.teamSize*(war.attacksPerMember??(cwl?1:2));
  const prep=war.state==='preparation',ended=war.state==='warEnded',time=warTime((prep?war.startTime:war.endTime)??'');
  const composition=(side:WarSide)=>{const map=new Map<number,number>();for(const m of side.members)map.set(m.townhallLevel,(map.get(m.townhallLevel)??0)+1);return [...map].sort((a,b)=>b[0]-a[0]).map(([th,n])=>`${emoji.get(th)} ${n}`).join('  ');};
  embed.fields=[{name:'War Against',value:`[**${escapeLinkLabel(other.name)} (${other.tag})**](${clanUrl(other.tag)})`,inline:false},
   {name:'War State',value:`${prep?'In Prep':ended?'War Over':'In War'} (${war.teamSize} vs ${war.teamSize})\n${prep?'Starting':ended?'Ended':'Ending'} ${Number.isFinite(time)?`<t:${Math.floor(time/1000)}:R>`:'Unavailable'}`,inline:false},
   {name:'War Stats',value:`\`${`${count(own)}/${max}`.padEnd(7)}\`${emoji.get('animated_clash_swords')}\`${`${count(other)}/${max}`.padStart(7)}\`\n\`${String(own.stars).padEnd(7)}\`${emoji.get('war_star')}\`${String(other.stars).padStart(7)}\`\n\`${`${own.destructionPercentage.toFixed(2)}%`.padEnd(7)}\`${emoji.get('broken_sword')}\`${`${other.destructionPercentage.toFixed(2)}%`.padStart(7)}\``,inline:false},
   {name:'War Composition',value:`${escapeMarkdown(own.name)}\n${composition(own)}\n${escapeMarkdown(other.name)}\n${composition(other)}`,inline:false}];
  const recent=[...own.members.flatMap(m=>(m.attacks??[]).map(hit=>({hit,name:m.name,icon:'clash_sword'}))),...other.members.flatMap(m=>(m.attacks??[]).map(hit=>({hit,name:own.members.find(p=>p.tag===hit.defenderTag)?.name??m.name,icon:'shield'})))].sort((a,b)=>b.hit.order-a.hit.order).slice(0,5);
  if(recent.length)embed.fields.push({name:'Last 5 attacks/defenses',value:recent.map(({hit,name,icon})=>`${emoji.get(icon)}\`${String(hit.destructionPercentage).padStart(3)}%\`${emoji.get('war_star').repeat(hit.stars)}${emoji.get('no_star').repeat(3-hit.stars)} ${escapeMarkdown(name)}`).join('\n'),inline:false});
 }else if(view==='opp_over'){
  const profile=await ctx.services.api.get<{name:string;description?:string;members?:number;clanLevel?:number;warWins?:number;warWinStreak?:number}>(`/v2/bot/clash/clans/${encodeURIComponent(other.tag)}`);
  embed.author={name:profile.name,...(other.badgeUrls?.small?{icon_url:other.badgeUrls.small}:{})};
  embed.description=`[${other.tag}](${clanUrl(other.tag)})\n${escapeMarkdown(profile.description??'')}\n\nLevel ${profile.clanLevel??'—'} | ${profile.members??'—'}/50\n${emoji.get('war_star')} ${profile.warWins??'—'} war wins | ${profile.warWinStreak??'—'} win streak`;
 }else{
  const side=['opponent','odefenses'].includes(view)?other:own,opposition=side===own?other:own;
  const lines=side.members.slice().sort((a,b)=>a.mapPosition-b.mapPosition).map((m,index)=>{
   const header=`\u200e\`${String(index+1).padStart(2)}\` ${emoji.get(m.townhallLevel)} \`${displayNameColumn(m.name,18)}\``;
   if(['roster','opponent'].includes(view))return header;
   const hits=view==='attacks'?(m.attacks??[]):opposition.members.flatMap(p=>p.attacks??[]).filter(a=>a.defenderTag===m.tag);
   return header+'\n'+(hits.length?hits.map(hit=>`${emoji.get('war_star').repeat(hit.stars)}${emoji.get('no_star').repeat(3-hit.stars)} \`${String(hit.destructionPercentage).padStart(3)}%\` #${opposition.members.find(p=>p.tag===(view==='attacks'?hit.defenderTag:hit.attackerTag))?.mapPosition??'?'}`).join('\n'):view==='attacks'?'No attacks used':'No defense recorded');
  });
  let text='';for(const line of lines){if(text.length+line.length+1>3600&&text){pages.push(text);text='';}text+=(text?'\n':'')+line;}if(text)pages.push(text);if(!pages.length)pages=['No members available.'];
  page=Math.min(page,pages.length-1);embed.title=title;embed.description=pages[page];
  if(pages.length>1)embed.footer!.text+=` | Page ${page+1} of ${pages.length}`;
 }
 const id=(v:string,p=0)=>`ck:war:war|${tag}|${period}|${v}|50|${p}`;
 const appUrl=`https://app.clashk.ing/clan/${encodeURIComponent(tag.replace(/^#/,''))}/war${period==='current'?'':`/${encodeURIComponent(period)}`}`;
 const controls=[actionRow({type:3,custom_id:id('select'),placeholder:title,options:warViews.map(([value,label,icon])=>({value,label,default:value===view,...(emoji.component(icon)?{emoji:emoji.component(icon)}:{})}))})];
 controls.push(actionRow(...(page>0?[{type:2 as const,style:2 as const,label:'Previous',custom_id:id(view,page-1)}]:[]),{type:2,style:2,emoji:emoji.component('refresh')??{name:'↻'},custom_id:id(view,page)},linkButton('Open in app',appUrl),...(page+1<pages.length?[{type:2 as const,style:2 as const,label:'Next',custom_id:id(view,page+1)}]:[])));
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[embed],components:controls});
}
