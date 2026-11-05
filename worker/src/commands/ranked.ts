import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, OptionType, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, fetchPlayer, pagedGameReply, personalPlayerAutocomplete, playerAppUrl, playerLabel, playerOption, playerUrl, resolvePlayerTag, subcommand, type Player } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { Command, CommandContext } from "./types";

export interface RankedHit { stars:number; destructionPercentage:number; trophies:number; creationTime:string; opponentName?:string }
export interface RankedMember { name:string; tag:string; trophies:number; attacks:number; wins:number; losses:number; defenses?:number; placement:number }
interface HistoryItem { mode:string; seasonId:string; leagueGroupId:string; league:{name:string}; leagueTrophies:number; placement:number; attackWins:number; attackLosses:number; maxBattles:number; defenseWins?:number; defenseLosses?:number }
interface LiveMember { playerName:string; playerTag:string; leagueTrophies:number; attackWinCount:number; attackLoseCount:number; defenseWinCount:number; defenseLoseCount:number }
interface RankedTierRules { _id:number; battle_count:number; promote_percentage:number; demote_percentage:number }
export interface RankedCutoffs { promotion?:number; demotion?:number }
let limits:Promise<Map<number,RankedTierRules>>|undefined,limitsExpiry=0;
async function rankedTierRules(tier:number){
 if(!limits||Date.now()>limitsExpiry){
  limitsExpiry=Date.now()+3600000;
  limits=fetch("https://assets.clashk.ing/static_data/league_tiers.json",{signal:AbortSignal.timeout(8000),redirect:"manual"}).then(async response=>{
   if(!response.ok)throw Error("League metadata unavailable");
   const body=await response.json() as {items:RankedTierRules[]};
   return new Map(body.items.map(item=>[item._id,item]));
  }).catch(error=>{limits=undefined;throw error;});
 }
 return (await limits).get(tier);
}
export async function rankedBattleLimit(tier:number){return (await rankedTierRules(tier))?.battle_count;}
export async function rankedOverview(ctx:CommandContext,player:Player){
 if(!player.currentLeagueGroupTag||!player.currentLeagueSeasonId)return undefined;
 const [group,limit]=await Promise.all([
  ctx.services.api.get<{members:LiveMember[]}>(`/v2/bot/clash/leaguegroup/${encodeURIComponent(player.currentLeagueGroupTag)}/${player.currentLeagueSeasonId}`,{playerTag:player.tag}),
  rankedBattleLimit(player.leagueTier?.id??0).catch(()=>undefined),
 ]);
 const member=group.members.find(item=>item.playerTag===player.tag);
 if(!member)return undefined;
 return {rank:1+group.members.filter(item=>item.leagueTrophies>member.leagueTrophies).length,attacks:member.attackWinCount+member.attackLoseCount,defenses:member.defenseWinCount+member.defenseLoseCount,limit};
}
const seasonOption={name:"season",description:"Ranked season (defaults to current)",type:OptionType.String};
export const rankedCommand:Command={
 deferred:true,
 definition:{name:"ranked",description:"Ranked players, season stats and groups",type:1,integration_types:[0,1],contexts:[0,1,2],options:[
  {name:"player",description:"View a Ranked player, season graphic and group",type:OptionType.Subcommand,options:[playerOption,seasonOption]},
  {name:"history",description:"View a player's Ranked season history",type:OptionType.Subcommand,options:[playerOption]},
 ]},autocomplete:personalPlayerAutocomplete,
 async execute(context){
  const ctx=subcommand(context),tag=await resolvePlayerTag(ctx),requested=stringOption(ctx,"season");
  if(ctx.path[0]==="history"){
   const [history,player,emoji]=await Promise.all([
    ctx.services.api.get<{items:HistoryItem[]}>(`/v2/player/${encodeURIComponent(tag)}/league/history`),
    fetchPlayer(ctx,tag).catch(()=>({name:tag})),emojis(ctx),
   ]);
   return pagedGameReply(ctx,`${player.name} · Ranked history`,history.items.filter(item=>item.mode==="ranked").map(item=>
    `**${escapeMarkdown(item.league.name)}** · ${seasonDate(item.seasonId)}\n${emoji.get("trophy")} **${item.leagueTrophies.toLocaleString("en")}** · #${item.placement} · ${item.attackWins+item.attackLosses}/${item.maxBattles} attacks`),"rh",[tag],tag);
  }
  const player=await fetchPlayer(ctx,tag);
  let season:string,league:string,members:RankedMember[],attackLogs:RankedHit[]=[],defenseLogs:RankedHit[]=[],maxBattles:number|undefined,cutoffs:RankedCutoffs|undefined;
  if(!requested){
   if(!player.currentLeagueGroupTag||!player.currentLeagueSeasonId)throw new CommandInputError("This player is not in a current Ranked tournament.");
   season=String(player.currentLeagueSeasonId);league=player.leagueTier?.name??"Ranked";
   const group=await ctx.services.api.get<{members:LiveMember[];attackLogs?:RankedHit[];defenseLogs?:RankedHit[]}>(`/v2/bot/clash/leaguegroup/${encodeURIComponent(player.currentLeagueGroupTag)}/${season}`,{playerTag:tag});
   const sorted=[...group.members].sort((a,b)=>b.leagueTrophies-a.leagueTrophies||a.playerTag.localeCompare(b.playerTag));
   members=sorted.map(item=>({name:item.playerName,tag:item.playerTag,trophies:item.leagueTrophies,attacks:item.attackWinCount+item.attackLoseCount,wins:item.attackWinCount,losses:item.attackLoseCount,defenses:item.defenseWinCount+item.defenseLoseCount,placement:sorted.findIndex(other=>other.leagueTrophies===item.leagueTrophies)+1}));
   const rules=await rankedTierRules(player.leagueTier?.id??0).catch(()=>undefined);
   if(rules){
    maxBattles=rules.battle_count;
    // These are live group boundary scores, not a prediction of the final
    // result. Round the actual membership, as the game does (94 × 15% = 14).
    // Never calculate against capacity or apply today's rules to old seasons.
    const promoted=Math.round(sorted.length*rules.promote_percentage/100),demoted=Math.round(sorted.length*rules.demote_percentage/100);
    cutoffs={promotion:promoted>0?sorted[promoted-1]?.leagueTrophies:undefined,demotion:demoted>0?sorted[sorted.length-demoted]?.leagueTrophies:undefined};
   }
   attackLogs=group.attackLogs??[];defenseLogs=group.defenseLogs??[];
  }else{
   season=requested;
   if(!/^[1-9][0-9]{0,15}$/u.test(season))throw new CommandInputError("Choose a valid Ranked season.");
   const history=await ctx.services.api.get<{items:HistoryItem[]}>(`/v2/player/${encodeURIComponent(tag)}/league/history`);
   const item=history.items.find(row=>row.mode==="ranked"&&row.seasonId===season);
   if(!item)throw new CommandInputError("No recorded Ranked tournament found for this player and season.");
   league=item.league.name;
   const group=await ctx.services.api.get<{maxBattles:number;members:Array<HistoryItem&{tag:string;name:string}>}>(`/v2/ranked/${season}/groups/${encodeURIComponent(item.leagueGroupId)}`);
   maxBattles=group.maxBattles;
   members=group.members.map(row=>({name:row.name,tag:row.tag,trophies:row.leagueTrophies,attacks:row.attackWins+row.attackLosses,wins:row.attackWins,losses:row.attackLosses,defenses:row.defenseWins===undefined?undefined:row.defenseWins+(row.defenseLosses??0),placement:row.placement}));
   const log=await ctx.services.api.get<{attacks:Array<{stars:number;destructionPercentage:number;trophies:number;time:string}>;defenses:Array<{stars?:number;destructionPercentage?:number;trophies:number;time?:string}>}>(`/v2/player/${encodeURIComponent(tag)}/ranked/${season}/battlelog`);
   attackLogs=log.attacks.map(hit=>({...hit,creationTime:hit.time}));
   defenseLogs=log.defenses.flatMap(hit=>hit.stars===undefined||!hit.time?[]:[{stars:hit.stars,destructionPercentage:hit.destructionPercentage??0,trophies:hit.trophies,creationTime:hit.time}]);
  }
  const member=members.find(item=>item.tag===tag);
  if(!member)throw new CommandInputError("This player's tournament membership is unavailable.");
  return rankedPlayerReply(ctx,player,league,season,members,member,attackLogs,defenseLogs,maxBattles,cutoffs);
 },
};
export function seasonDate(season:string){const date=new Date(Number(season)*1000);return Number.isFinite(date.getTime())?date.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}):season;}
async function rankedPlayerReply(ctx:CommandContext,player:Player,league:string,season:string,members:RankedMember[],member:RankedMember,attacks:RankedHit[],defenses:RankedHit[],maxBattles?:number,cutoffs?:RankedCutoffs){
 const emoji=await emojis(ctx),view=stringOption(ctx,"__view")??(ctx.path[0]==="group"?"group":"overview");
 const requested=stringOption(ctx,"season")??"current",owner=invokingUserId(ctx);
 const id=(page:string,index:number)=>`ck:page:rp:${owner}:${player.tag}:${requested}:${page}:${index}`;
 const rankIcon=emoji.get(league)||emoji.get("trophy");
 let response;
 if(view==="group"){
  response=await pagedGameReply(ctx,`${league} · Group`,members.map(item=>`\u2066**${emoji.number(item.placement)} ${playerLabel({name:`\u2068${item.name.replace(/[\u202a-\u202e\u2066-\u2069]/gu,"")}\u2069`,tag:item.tag})}**\u2069\n-# ${emoji.get("trophy")} **${item.trophies.toLocaleString("en")}** · ${item.attacks}${maxBattles?`/${maxBattles}`:""} attacks`),"rp",[player.tag,requested,"group"]);
 }else{
  const hitLines=(hits:RankedHit[])=>hits.slice(-8).map(hit=>`${hit.trophies>=0?"+":""}${hit.trophies} <t:${Math.floor(Date.parse(hit.creationTime)/1000)}:R>`).join("\n")||"None recorded yet.";
  response=legacyMessage({allowed_mentions:{parse:[]},embeds:[{
   author:{name:`${player.name}${player.clan?` | ${player.clan.name}`:""}`.slice(0,256),url:playerUrl(player.tag),...(player.clan?.badgeUrls?.small?{icon_url:player.clan.badgeUrls.small}:{})},
   title:league,url:playerAppUrl(player.tag,ctx.env.APP_ENV),color:await serverEmbedColor(ctx),
   thumbnail:{url:`https://assets.clashk.ing/buildings/home-village/town_hall/level_${player.townHallLevel}.webp`},
   description:`${rankIcon} **${member.trophies.toLocaleString("en")}** · **#${member.placement}** / ${members.length}\n[Player profile](${playerUrl(player.tag)}) · [ClashKing](${playerAppUrl(player.tag,ctx.env.APP_ENV)})`,
   fields:[
    {name:`Attacks (${member.attacks}${maxBattles?`/${maxBattles}`:""})`,value:`-# ${member.wins} wins · ${member.losses} losses\n${hitLines(attacks)}\n\u200b`,inline:true},
    {name:`Defenses${member.defenses===undefined?"":` (${member.defenses})`}`,value:hitLines(defenses)+"\n\u200b",inline:true},
   ],footer:{text:seasonDate(season)},image:{url:"attachment://ranked-season.png"},
  }],components:[]});
  const {rankedPoster}=await import("./ranked-poster");
  response.data!.__files=[{name:"ranked-season.png",bytes:await rankedPoster({player,league,season,members,member,attacks,defenses,cutoffs})}];
 }
 const pages=(response.data!.components as unknown[]??[]);
 const currentPage=Number(ctx.options.get("__page")?.value??0);
 response.data!.components=[actionRow(
  {type:2,style:2,label:"Player",custom_id:id("overview",0),disabled:view!=="group"},
  {type:2,style:2,label:"Group",custom_id:id("group",view==="group"?currentPage:0),disabled:view==="group"},
 ),...pages];
 if(view==="group")response.data!.attachments=[];
 return response;
}
