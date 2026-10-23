import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, invokingUserId, normalizeTag, OptionType, stringOption } from "./command-utils";
import { compact, emojis, escapeMarkdown, fetchPlayer, subcommand } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { displayNameColumn } from "./display-width";
import type { Command } from "./types";

interface Member {tag:string;name:string;role?:string;townHallLevel?:number;donations?:number;donationsReceived?:number}
interface Clan {name:string;tag:string;description?:string;type?:string;clanLevel:number;members:number;clanPoints:number;clanBuilderBasePoints?:number;clanCapitalPoints?:number;requiredTrophies?:number;requiredTownhallLevel?:number;warWins?:number;warLosses?:number;warTies?:number;warWinStreak?:number;isWarLogPublic?:boolean;warLeague?:{name:string};capitalLeague?:{name:string};location?:{name:string;countryCode?:string};badgeUrls?:{small?:string;large?:string};memberList:Member[];clanCapital?:{districts:Array<{id:number;districtHallLevel:number}>}}
interface Contribution {tag:string;name:string;townHallLevel:number;donated:number;received:number;clanGames:number;capitalDonated:number}
interface SeasonStats {season:string;current:boolean;truncated:boolean;activeDaily:number;items:Contribution[]}
const safe=(text:string)=>`\u2068${escapeMarkdown(text.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,""))}\u2069`;
const clanUrl=(tag:string)=>`https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(tag)}`;
const clanOption={name:"clan",description:"Clan tag or name",type:OptionType.String,required:true,autocomplete:true};

export const clanCommand:Command={
 deferred:true,
 definition:{name:"clan",description:"Clan overview and season donations",type:1,integration_types:[0,1],contexts:[0,1,2],options:[
  {name:"search",description:"View a clan overview",type:OptionType.Subcommand,options:[clanOption,{name:"type",description:"Overview style (default Detailed)",type:OptionType.String,choices:[{name:"Detailed",value:"d"},{name:"Basic",value:"b"},{name:"Minimalistic",value:"m"}]}]},
  {name:"donations",description:"View current or historical clan donations",type:OptionType.Subcommand,options:[clanOption,
   {name:"season",description:"Season YYYY-MM (defaults to current)",type:OptionType.String},
   {name:"townhall",description:"Only show this Town Hall",type:OptionType.Integer,min_value:1,max_value:18},
   {name:"limit",description:"Number of players (default 50)",type:OptionType.Integer,min_value:1,max_value:50},
   {name:"sort_by",description:"Sort players by (default Donations)",type:OptionType.String,choices:[{name:"Donations",value:"donated"},{name:"Received",value:"received"},{name:"Name",value:"name"},{name:"Town Hall",value:"townHallLevel"}]},
   {name:"sort_order",description:"Sort direction (default Descending)",type:OptionType.String,choices:[{name:"Descending",value:"desc"},{name:"Ascending",value:"asc"}]},
  ]},
 ]},
 async autocomplete(context){
  const ctx=subcommand(context),query=String(ctx.options.get("clan")?.value??"").trim();
  if(!query&&ctx.interaction.guild_id){
   const clans=await ctx.services.api.get<Array<{name:string;tag:string}>>(`/v2/server/${ctx.interaction.guild_id}/clans-basic`);
   return clans.slice(0,25).map(clan=>({name:`${clan.name} | ${clan.tag}`.slice(0,100),value:clan.tag}));
  }
  if(!query)return [];
  const result=await ctx.services.api.get<{items:Array<{name:string;tag:string;clanLevel:number}>}>("/v2/clan/search",{query,limit:25});
  return result.items.map(clan=>({name:`${clan.name} | Lv${clan.clanLevel} | ${clan.tag}`.slice(0,100),value:clan.tag}));
 },
 async execute(context){
  const ctx=subcommand(context),raw=stringOption(ctx,"clan");if(!raw)throw new CommandInputError("Choose a clan or enter its tag.");
  const tag=normalizeTag(raw,ctx.locale),view=ctx.path[0]==="donations"?"d":"o";
  const membersOnly=stringOption(ctx,"__members_only")==="true";
  const style=stringOption(ctx,"type")??"d";
  if(!["d","b","m"].includes(style))throw new CommandInputError("Choose a valid overview style.");
  const season=stringOption(ctx,"season")??"current",hall=Number(ctx.options.get("townhall")?.value??0),limit=Number(ctx.options.get("limit")?.value??50),sort=stringOption(ctx,"sort_by")??"donated",order=stringOption(ctx,"sort_order")??"desc";
  if(season!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))throw new CommandInputError("Use a season in YYYY-MM format.");
  if(!Number.isInteger(hall)||hall<0||hall>18||!Number.isInteger(limit)||limit<1||limit>50||!["donated","received","name","townHallLevel"].includes(sort)||!["asc","desc"].includes(order))throw new CommandInputError("Choose valid donation filters.");
  const [clan,emoji,stats,color]=await Promise.all([
   ctx.services.api.get<Clan>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`),emojis(ctx),
   ctx.services.api.get<SeasonStats>(`/v2/bot/clans/${encodeURIComponent(tag)}/season-stats`,season==="current"?{}:{season}),serverEmbedColor(ctx),
  ]);
  const rows=new Map(stats.items.map(row=>[row.tag,{...row}]));
  if(stats.current)for(const member of clan.memberList){
   const observed=rows.get(member.tag);
   // Match the old current-season fallback, never use it for a past season.
   // A member's live counters are season-wide, while stored events are clan-attributed.
   rows.set(member.tag,{tag:member.tag,name:member.name,townHallLevel:member.townHallLevel??observed?.townHallLevel??0,donated:Math.max(member.donations??0,observed?.donated??0),received:Math.max(member.donationsReceived??0,observed?.received??0),clanGames:observed?.clanGames??0,capitalDonated:observed?.capitalDonated??0});
  }
  const all=[...rows.values()],total=(key:"donated"|"received"|"clanGames"|"capitalDonated")=>all.reduce((sum,row)=>sum+row[key],0);
  let description:string,footer:string,displayed=0;
  const fields:Array<{name:string;value:string;inline:false}>=[];
  if(view==="o"){
   const flag=clan.location?.countryCode&&/^[A-Z]{2}$/u.test(clan.location.countryCode)?String.fromCodePoint(...[...clan.location.countryCode].map(letter=>127397+letter.charCodeAt(0))):"🌍";
   const leader=clan.memberList.find(member=>member.role==="leader");
   const types:Record<string,string>={open:"Anyone Can Join",inviteOnly:"Invite Only",invite_only:"Invite Only",closed:"Closed"};
   const halls=new Map<number,number>();for(const member of clan.memberList){const th=member.townHallLevel??0;if(th)halls.set(th,(halls.get(th)??0)+1);}
   const composition=[...halls].sort((a,b)=>b[0]-a[0]).map(([th,count])=>`${emoji.get(th)} ${count}`);
   const compositionLines=[];for(let i=0;i<composition.length;i+=4)compositionLines.push(composition.slice(i,i+4).join("  "));
   const capitalHall=clan.clanCapital?.districts.find(district=>district.id===70000000)?.districtHallLevel;
   const ratio=clan.isWarLogPublic?((clan.warWins??0)/Math.max(1,clan.warLosses??0)).toFixed(2):"Hidden Log";
   const ranking=style==="d"?await ctx.services.api.get<{homeVillage:{placements:Array<{locationId:string;rank:number}>}}>(`/v2/clan/${encodeURIComponent(tag)}/rankings`).catch(()=>undefined):undefined;
   const placements=ranking?.homeVillage.placements??[],global=placements.find(row=>row.locationId==="global"),local=placements.find(row=>row.locationId!=="global");
   description=style==="m"?`**[${safe(clan.name)}](${clanUrl(tag)})**\n${clan.members}/50 members\n${clan.warLeague?.name??"Unranked"}`:[
    `Tag: [${clan.tag}](${clanUrl(tag)})\nTrophies: ${emoji.get("trophy")} ${clan.clanPoints.toLocaleString("en")} | ${emoji.get("versus_trophy")} ${(clan.clanBuilderBasePoints??0).toLocaleString("en")}\n${style==="d"?`Requirements: ${emoji.get("trophy")} ${clan.requiredTrophies??0} | ${emoji.get(clan.requiredTownhallLevel??1)} ${clan.requiredTownhallLevel??1}\nType: ${types[clan.type??""]??"Not set"}`:`Required Trophies: ${emoji.get("trophy")} ${clan.requiredTrophies??0}`}\nLocation: ${flag} ${safe(clan.location?.name??"Not Set")}${global||local?`\nRankings: ${global?`🌍 #${global.rank}`:""}${local?` ${flag} #${local.rank}`:""}`:""}`,
    `Leader: ${leader?safe(leader.name):"Not available"}\nLevel: ${clan.clanLevel}\nMembers: ${emoji.get("people")} ${clan.members}/50`,
    `CWL: ${emoji.get(`cwl${clan.warLeague?.name??""}`)} ${clan.warLeague?.name??"Unranked"}\nWars Won: ${emoji.get("up_green_arrow")} ${clan.warWins??0}\nWars Lost: ${emoji.get("down_red_arrow")} ${clan.isWarLogPublic?clan.warLosses??0:"Hidden Log"}\nWar Streak: ${emoji.get("double_up_arrow")} ${clan.warWinStreak??0}\nWinratio: ${ratio}`,
    ...(style==="d"?[`Capital League: ${emoji.get(clan.capitalLeague?.name??"capital_trophy")} ${clan.capitalLeague?.name??"Unranked"}\nCapital Points: ${emoji.get("capital_trophy")} ${clan.clanCapitalPoints??0}\nCapital Hall: ${emoji.get(`capital_hall${capitalHall??1}`)} Level ${capitalHall??0}`]:[]),
    `Description: ${escapeMarkdown(clan.description??"")}`,
   ].join("\n\n");footer=stats.season;
   if(style==="d"){
    fields.push({name:"Season Stats",value:`Clan Games: ${compact(total("clanGames"))} Points\nCap Gold: ${compact(total("capitalDonated"))} Donated\nDonos: ${emoji.get("up_green_arrow")} ${compact(total("donated"))}, ${emoji.get("down_red_arrow")} ${compact(total("received"))}\nActive Daily: ${stats.activeDaily} players/avg\n\u200b`,inline:false});
    if(composition.length)fields.push({name:"Townhall Composition:",value:compositionLines.join("\n")+"\n\u200b",inline:false});
    const boosted=new Map<string,number>();
    for(let i=0;i<clan.memberList.length;i+=5){
     const players=await Promise.all(clan.memberList.slice(i,i+5).map(member=>fetchPlayer(ctx,member.tag).catch(()=>undefined)));
     for(const player of players)for(const troop of player?.troops??[])if(troop.superTroopIsActive)boosted.set(troop.name,(boosted.get(troop.name)??0)+1);
    }
    fields.push({name:"Boosted Super Troops:",value:[...boosted].map(([name,count])=>`${emoji.get(name)} ${count}`).join(" ")||"None",inline:false});
   }
  }else{
   const currentTags=new Set(clan.memberList.map(member=>member.tag));
   const filtered=all.filter(row=>(!hall||row.townHallLevel===hall)&&(!membersOnly||!stats.current||currentTags.has(row.tag)));
   filtered.sort((a,b)=>{const cmp=sort==="name"?a.name.localeCompare(b.name):Number(a[sort as "donated"|"received"|"townHallLevel"])-Number(b[sort as "donated"|"received"|"townHallLevel"]);return (order==="asc"?cmp:-cmp)||a.tag.localeCompare(b.tag);});
   const selected=filtered.slice(0,limit);displayed=selected.length;
   // Keep the Town Hall column before the name, using normal monospace digits.
   description=selected.length?"` #  DON   REC  TH NAME         `\n"+selected.map((row,index)=>{
    const name=displayNameColumn(row.name,13);
    return `\u2066\`${String(index+1).padStart(2)} ${compact(row.donated).padStart(5)} ${compact(row.received).padStart(5)} ${(row.townHallLevel?String(row.townHallLevel):"?").padStart(2)} \u2068${name}\u2069\`\u2069`;
   }).join("\n"):"No recorded donations for this season and filter.";
   footer=`▲ ${compact(filtered.reduce((sum,row)=>sum+row.donated,0))}  ▼ ${compact(filtered.reduce((sum,row)=>sum+row.received,0))} · ${stats.season}${stats.truncated?" · Partial recorded data":""}`;
  }
  const id=(mode:string,index:number,only=membersOnly)=>["ck","page","cl",invokingUserId(ctx),tag,mode,season,hall,limit,sort,order,only?"m":"a",style,index].join(":");
  const refresh=emoji.component("refresh");
  const components=[actionRow(
   {type:2,style:2,...(refresh?{emoji:{id:refresh.id,name:refresh.name}}:{label:"Refresh"}),custom_id:id(view.toUpperCase(),0)},
   ...(view==="o"?[{type:2 as const,style:5 as const,label:"Open In-Game",url:clanUrl(tag)}]:[]),
   ...(view==="d"&&stats.current?[{type:2 as const,style:2 as const,label:membersOnly?"Include former members":"Current members only",custom_id:id(view,0,!membersOnly)}]:[]),
  )];
  return legacyMessage({allowed_mentions:{parse:[]},embeds:[{...(view==="o"?{title:clan.name}:{author:{name:`${clan.name} Top ${displayed} Donators`,...(clan.badgeUrls?.small?{icon_url:clan.badgeUrls.small}:{})}}),...(view==="o"&&clan.badgeUrls?.large?{thumbnail:{url:clan.badgeUrls.large}}:{}),color,description,...(fields.length?{fields}:{}),footer:{text:footer}}],components});
 },
};
