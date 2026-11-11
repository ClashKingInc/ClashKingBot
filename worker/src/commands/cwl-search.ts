import { editOriginalInteractionResponse } from "../discord/message-actions";
import { sendInteractionError } from "./errors";
import { actionRow, legacyMessage, linkButton, type LegacyEmbed } from '../discord/components';
import { InteractionResponseType } from '../discord/types';
import { CommandInputError, normalizeTag, stringOption } from './command-utils';
import { compactTableRow, COMPACT_TABLE, isolatedNameColumn as displayNameColumn } from './display-width';
import { emojis, escapeMarkdown, escapeLinkLabel } from './game-common';
import { serverEmbedColor } from './embed-color';
import { warAttackAllowance, clanRounds, cwlRanking, latestWar, loadCwl, warTime, type War, type WarSide } from './war-data';
import type { CommandContext } from './types';

const clanUrl=(tag:string)=>`https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(tag)}`;
const pages = [
 ['overview','Current Round','animated_clash_swords'],['lineup','Current Lineup','troop'],
 ['attacks','Attacks','thick_capital_sword'],['defenses','Defenses','shield'],
 ['next','Next Round','forward'],['nextlineup','Next Round Lineup','troop'],['opponent','Next Opponent Overview','search'],
 ['stars','Player Leaderboards','war_star'],['rankings','Clan Leaderboard','up_green_arrow'],
 ['townhalls','Town Hall Breakdown','townhall'],
 ['missed','Missed Hits','square_x_deny'],['rounds','All Rounds','wrench'],['members','All Members','people'],
] as const;
interface State { source:string; tag:string; season:string; page:string; round?:number }
const count=(side:WarSide)=>side.members.reduce((sum,member)=>sum+(member.attacks?.length??0),0);
const ownSides=(war:War,tag:string)=>war.clan.tag===tag?[war.clan,war.opponent] as const:[war.opponent,war.clan] as const;
const stamp=(value:string|undefined)=>value&&Number.isFinite(warTime(value))?`<t:${Math.floor(warTime(value)/1000)}:R>`:'Unavailable';
const crop=(lines:string[],budget=3800)=>{let value='';for(const line of lines){if(value.length+line.length+1>budget)break;value+=(value?'\n':'')+'\u200e'+line;}return value;};

export async function cwlSearch(ctx:CommandContext,state?:State){
 const tag=state?.tag??normalizeTag(stringOption(ctx,'clan')??'',ctx.locale);
 const source=state?.source??tag,season=state?.season??stringOption(ctx,'season')??new Date().toISOString().slice(0,7);
 if(!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))throw new CommandInputError('Choose a season in YYYY-MM format.');
 const data=await loadCwl(ctx,source,season);
 const color=await serverEmbedColor(ctx),emoji=await emojis(ctx);
 if(!data)return legacyMessage({content:`No CWL is available for ${tag} in ${season}.`});
 const {group,wars}=data;
 if(!group.warLeague){const profile=await ctx.services.api.get<{warLeague?:{id:number;name:string}}>(`/v2/bot/clash/clans/${encodeURIComponent(source)}`);group.warLeague=profile.warLeague;}
 const clan=group.clans.find(clan=>clan.tag===tag);
 if(!clan)throw new CommandInputError('Choose a clan in this CWL group.');
 const rounds=clanRounds(group,wars,tag),latest=latestWar(wars,tag);
 const defaultRound=Math.max(0,rounds.findIndex(war=>war===latest));
 const round=state?.round??defaultRound,page=state?.page??'overview';
 if(!pages.some(([key])=>key===page)||!Number.isInteger(round)||round<0||round>=Math.max(1,rounds.length))throw new CommandInputError('Choose a valid CWL page or round.');
 const current=rounds[round],next=rounds[round+1];
 const embed=(title:string,description?:string):LegacyEmbed=>({title,color,...(description?{description}:{}),...(clan.badgeUrls?.small?{thumbnail:{url:clan.badgeUrls.small}}:{}),footer:{text:season}});
 const overview=(war:War,index:number):LegacyEmbed=>{
  const [own,other]=ownSides(war,tag),prep=war.state==='preparation',ended=war.state==='warEnded';
  const fields:NonNullable<LegacyEmbed['fields']>=[
   {name:'War Against',value:`[**${escapeLinkLabel(other.name)} (${other.tag})**](${clanUrl(other.tag)})`,inline:false},
   {name:'War State',value:[group.warLeague?`${emoji.get(group.warLeague.name)} ${group.warLeague.name}`:'',`${prep?'In Prep':ended?'War Over':'In War'} (${war.teamSize} vs ${war.teamSize})`,`${prep?'Starting':ended?'Ended':'Ending'} ${stamp(prep?war.startTime:war.endTime)}`].filter(Boolean).join('\n'),inline:false},
   {name:'War Stats',value:`\`${`${count(own)}/${war.teamSize}`.padEnd(7)}\`${emoji.get('animated_clash_swords')}\`${`${count(other)}/${war.teamSize}`.padStart(7)}\`\n\`${String(own.stars).padEnd(7)}\`${emoji.get('war_star')}\`${String(other.stars).padStart(7)}\`\n\`${`${own.destructionPercentage.toFixed(2)}%`.padEnd(7)}\`${emoji.get('broken_sword')}\`${`${other.destructionPercentage.toFixed(2)}%`.padStart(7)}\``,inline:false},
  ];
  const composition=(side:WarSide)=>{
   const halls=new Map<number,number>();for(const member of side.members)halls.set(member.townhallLevel,(halls.get(member.townhallLevel)??0)+1);
   return [...halls].sort((a,b)=>b[0]-a[0]).map(([hall,amount])=>`${emoji.get(hall)} ${amount}`).join('  ');
  };
  fields.push({name:'War Composition',value:`${own.name}\n${composition(own)}\n${other.name}\n${composition(other)}`,inline:false});
  const recent=[...own.members.flatMap(member=>(member.attacks??[]).map(hit=>({hit,name:member.name,icon:'clash_sword'}))),...other.members.flatMap(member=>(member.attacks??[]).map(hit=>({hit,name:own.members.find(p=>p.tag===hit.defenderTag)?.name??member.name,icon:'shield'})))].sort((a,b)=>b.hit.order-a.hit.order).slice(0,5);
  if(recent.length)fields.push({name:'Last 5 attacks/defenses',value:recent.map(({hit,name,icon})=>`${emoji.get(icon)}\`${String(hit.destructionPercentage).padStart(3)}%\`${emoji.warStars(hit.stars)} ${escapeMarkdown(name)}`).join('\n'),inline:false});
  return {...embed(own.name),fields,footer:{text:`${season} | Round ${index+1}`}};
 };
 const lineup=(war:War,index:number)=>ownSides(war,tag).map(side=>({...embed(`${side.name} Lineup`,crop(side.members.slice().sort((a,b)=>a.mapPosition-b.mapPosition).map((member,position)=>`\`${String(position+1).padStart(2)}\` ${emoji.get(member.townhallLevel)} \`${compactTableRow([{value:member.name,width:20,isolate:true}],5+COMPACT_TABLE.iconColumns)}\``))),footer:{text:`${season} | Round ${index+1}`}}));
 let embeds:LegacyEmbed[];
 if(page==='townhalls'){
  // Use war-side members, never the season roster: registered substitutes
  // must not inflate a clan's currently fielded Town Hall composition.
  const fields=group.clans.flatMap(groupClan=>{
   const war=latestWar(wars.filter(war=>war.state==='inWar'||war.state==='preparation'),groupClan.tag);
   if(!war)return [];
   const [side]=ownSides(war,groupClan.tag),halls=new Map<number,number>();
   for(const member of side.members)halls.set(member.townhallLevel,(halls.get(member.townhallLevel)??0)+1);
   return [{name:`\u200e${displayNameColumn(escapeMarkdown(side.name),100,100).trimEnd()}`,value:[...halls].sort((a,b)=>b[0]-a[0]).map(([hall,amount])=>`${emoji.get(hall)} \`${String(amount).padStart(2)}\``).join('  '),inline:false}];
  });
  embeds=[{...embed('Town Hall Breakdown',fields.length?undefined:'No current lineups available.'),fields}];
 }else if(page==='rankings'){
  const lines=cwlRanking(group,wars).map(([,score])=>`\u200e\`${compactTableRow([String(score.rank).padStart(2),String(score.stars).padStart(3),`${score.destruction.toFixed(2).padStart(7)}%`,{value:score.name,width:15,isolate:true}])}\``);
  embeds=[embed('Clan Ranking Leaderboard',`\` #  ST    DSTR Name\`\n${lines.join('\n')}`)];
 }else if(page==='rounds'){
  embeds=[{...embed(`${clan.name} CWL (All Rounds)`),fields:rounds.flatMap((war,index)=>{
   if(!war)return [];
   const [own,other]=ownSides(war,tag),ended=war.state==='warEnded',prep=war.state==='preparation';
   const difference=own.stars-other.stars||own.destructionPercentage-other.destructionPercentage;
   const result=ended?(difference>0?'Won':difference<0?'Lost':'Tied'):'';
   const maximum=war.teamSize*warAttackAllowance(war,true);
   return [{name:`${own.name} vs ${other.name}\nRound ${index+1} | ${prep?'In Prep':ended?'War Over':'In War'}${result?` (${result})`:''}`,
    value:`\`${`${count(own)}/${maximum}`.padEnd(7)}\`${emoji.get('animated_clash_swords')}\`${`${count(other)}/${maximum}`.padStart(7)}\`\n`+
      `\`${String(own.stars).padEnd(7)}\`${emoji.get('war_star')}\`${String(other.stars).padStart(7)}\`\n`+
      `\`${`${own.destructionPercentage.toFixed(2)}%`.padEnd(7)}\`${emoji.get('broken_sword')}\`${`${other.destructionPercentage.toFixed(2)}%`.padStart(7)}\`\n`+
      `${prep?'Starting':ended?'Ended':'Ending'} ${stamp(prep?war.startTime:war.endTime)}`,inline:false}];
  })}];
 }else if(page==='stars'||page==='missed'){
  const ownWars=rounds.filter((war):war is War=>!!war);
  const leaderboard=(defense:boolean)=>{
   const records=new Map<string,{name:string;hall:number;stars:number;destruction:number;hits:number;rounds:number}>();
   // Preparation members belong on the leaderboard at zero; only started
   // rounds contribute to their attack denominator or missed-attack count.
   for(const war of ownWars){if(page==='missed'&&war.state!=='warEnded')continue;const [own,other]=ownSides(war,tag);
    for(const member of own.members){const row=records.get(member.tag)??{name:member.name,hall:member.townhallLevel,stars:0,destruction:0,hits:0,rounds:0};if(war.state!=='preparation')row.rounds++;
     const hits=defense?other.members.flatMap(p=>p.attacks??[]).filter(hit=>hit.defenderTag===member.tag).sort((a,b)=>b.stars-a.stars||b.destructionPercentage-a.destructionPercentage).slice(0,1):member.attacks??[];
     row.hits+=hits.length;for(const hit of hits){row.stars+=hit.stars;row.destruction+=hit.destructionPercentage;}records.set(member.tag,row);
    }
   }
   return [...records.values()].sort((a,b)=>page==='missed'?(b.rounds-b.hits)-(a.rounds-a.hits):b.stars-a.stars||b.destruction-a.destruction);
  };
  if(page==='missed')embeds=[embed(`${clan.name} CWL Missed Hits`,crop(leaderboard(false).filter(row=>row.rounds>row.hits).map(row=>`${emoji.get(row.hall)} \`${compactTableRow([String(row.rounds-row.hits).padStart(2),{value:row.name,width:18,isolate:true}],COMPACT_TABLE.iconColumns)}\``))||'No missed hits.')];
  else embeds=[false,true].map(defense=>embed(`${clan.name} ${defense?'Defense':'Offense'} Leaderboard`,crop(['` # HIT ST   DSTR Name`',...leaderboard(defense).map((row,index)=>`\`${compactTableRow([String(index+1).padStart(2),`${row.hits}/${row.rounds}`.padStart(3),String(row.stars).padStart(2),`${row.destruction.toFixed(0).padStart(5)}%`,{value:row.name,width:15,isolate:true}])}\``)],2500)));
 }else if(page==='members'){
  embeds=[embed(`${clan.name} CWL Members`,crop((clan.members??[]).map((member,index)=>`\`${String(index+1).padStart(2)}\` ${emoji.get(member.townHallLevel??member.townhallLevel??0)} \`${compactTableRow([{value:member.name,width:20,isolate:true}],5+COMPACT_TABLE.iconColumns)}\``))||'Registered members unavailable.')];
 }else if(page==='lineup'||page==='nextlineup'){
  const war=page==='lineup'?current:next;embeds=war?lineup(war,round+(page==='nextlineup'?1:0)):[embed('Lineup','That round has not been assigned yet.')];
 }else if(page==='attacks'||page==='defenses'){
  if(!current)embeds=[embed(clan.name,'That round has not been assigned yet.')];
  else {const [own,other]=ownSides(current,tag),opponents=new Map(other.members.map(member=>[member.tag,member]));
   embeds=[embed(`${clan.name} ${page==='attacks'?'War Attacks':'Defenses Taken'}`,crop(own.members.slice().sort((a,b)=>a.mapPosition-b.mapPosition).map(member=>{
    const hits=page==='attacks'?member.attacks??[]:other.members.flatMap(p=>p.attacks??[]).filter(hit=>hit.defenderTag===member.tag);
    return `${emoji.get(member.townhallLevel)} **${escapeMarkdown(member.name)}**\n${hits.length?hits.map(hit=>`${hit.destructionPercentage}% ${emoji.warStars(hit.stars)} (#${opponents.get(page==='attacks'?hit.defenderTag:hit.attackerTag)?.mapPosition??'?'})`).join('\n'):page==='attacks'?'No attacks used':'No defenses taken'}`;
   })))];}
 }else{
  const war=page==='next'||page==='opponent'?next:current;
  if(!war)embeds=[embed(clan.name,'That round has not been assigned yet.')];
  else if(page==='opponent'){const [,other]=ownSides(war,tag);embeds=[embed(`${other.name} (Next Opponent)`,crop(other.members.map(member=>`${emoji.get(member.townhallLevel)} ${escapeMarkdown(member.name)}`)))];}
  else embeds=[overview(war,round+(page==='next'?1:0))];
 }
 const id=(control:string)=>`ck:cwl:${source}|${tag}|${season}|${page}|${round}|${control}`;
 const choices=pages.filter(([key])=>!['next','nextlineup','opponent'].includes(key)||!!next).map(([value,label,icon])=>({value,label,default:value===page,...(emoji.component(icon)?{emoji:emoji.component(icon)}:{})}));
 const appUrl=new URL(`https://app.clashk.ing/clan/${encodeURIComponent(tag.replace(/^#/,''))}/cwl`);appUrl.searchParams.set('season',season);
 const components=[actionRow({type:3,custom_id:id('page'),placeholder:'CWL pages',options:choices}),actionRow({type:3,custom_id:id('round'),placeholder:`Round ${round+1}`,options:rounds.flatMap((war,index)=>war?[{label:`Round ${index+1}`,value:String(index),default:index===round}]:[])}),actionRow({type:3,custom_id:id('clan'),placeholder:clan.name,options:group.clans.map(clan=>({label:clan.name.slice(0,100),value:clan.tag,default:clan.tag===tag}))}),actionRow({type:2,style:2,custom_id:id('refresh'),emoji:emoji.component('refresh')??{name:'↻'}},linkButton('Open in app',appUrl.toString()))];
 if(!rounds.some(Boolean))components.splice(1,1);
 return legacyMessage({allowed_mentions:{parse:[]},embeds,components});
}

export async function dispatchCwlSearch(ctx:CommandContext,waitUntil?:(promise:Promise<unknown>)=>void){
 const parts=(ctx.interaction.data?.custom_id??'').slice('ck:cwl:'.length).split('|');
 if(parts.length!==6)throw new CommandInputError('Invalid CWL control.');
 const [source,tag,season,page,round,control]=parts;
 const state:State={source:normalizeTag(source!,ctx.locale),tag:normalizeTag(tag!,ctx.locale),season:season!,page:page!,round:Number(round)};
 const values=ctx.interaction.data?.values;
 if(control!=='refresh'&&values?.length!==1)throw new CommandInputError('Choose a CWL option.');
 if(control==='page')state.page=values![0]!;
 else if(control==='round'){state.round=Number(values![0]);state.page='overview';}
 else if(control==='clan'){state.tag=normalizeTag(values![0]!,ctx.locale);state.round=undefined;state.page='overview';}
 else if(control!=='refresh')throw new CommandInputError('Invalid CWL control.');
 const run=cwlSearch(ctx,state);
 if(!waitUntil)return {...await run,type:InteractionResponseType.UpdateMessage};
 waitUntil(run.then(reply=>editOriginalInteractionResponse(ctx.services.discordRest,ctx.interaction.token,reply.data??{})).catch((error)=>sendInteractionError(ctx,error)));
 return {type:InteractionResponseType.DeferredUpdateMessage};
}
