import { actionRow, legacyMessage, type LegacyEmbed } from "../discord/components";
import { invokingUserId } from "./command-utils";
import { serverEmbedColor } from "./embed-color";
import { emojis, legendDay, playerAppUrl, playerUrl, type Player } from "./game-common";
import type { CommandContext } from "./types";

export interface LegendSeasonSummary {
  seasonStart:string;seasonEnd:string;
  rankPopulation?:number;
  favorites?:Array<{category:"troop"|"spell"|"hero"|"equipment"|"pet"|"siege";id:number;name:string;attacks:number}>;
  favoriteTroops?:Array<{id:number;name:string;attacks:number;triples:number}>;
  armyGroups?:Array<{name:string;attacks:number;triples:number}>;
  stats:{attacks:number;defenses:number;attackTriples:number;defenseTriples:number;averageOffense:number|null;averageDefense:number|null;offenseStars?:{zero:number;one:number;two:number;three:number};defenseStars?:{zero:number;one:number;two:number;three:number}};
}
export interface LegendSeasonDay {day:string;attackTrophies:number;defenseTrophies:number;trophies:number;closingTrophies?:number|null;attacks?:number;defenses?:number;recordedDefenses?:number;automaticDefenses?:number}
export interface LegendDayBattle { trophies:number;stars?:number;automatic?:boolean;time?:string }
export interface LegendDayDetails {
  day:string;attackTrophies:number;defenseTrophies:number;trophies:number;
  attacks:LegendDayBattle[];defenses:LegendDayBattle[];
  topArmy?:{name:string;attacks:number;triples:number};
}
const signed=(value:number)=>`${value>=0?"+":""}${value.toLocaleString("en")}`;
const percent=(count:number,total:number)=>total?`${(count/total*100).toFixed(1)}%`:"—";
const shiftDay=(day:string,delta:number)=>new Date(Date.parse(day)+delta*86400000).toISOString().slice(0,10);

/** Day numbers use the API's season boundary, not the index of available rows.
 * Keep recorded battle statistics separate from inferred automatic defenses. */
export async function legendSeasonReply(ctx:CommandContext,player:Pick<Player,"name"|"tag">&Partial<Player>&{globalRank?:number;location?:{name:string;countryCode?:string}},season:LegendSeasonSummary,days:LegendSeasonDay[],townHallIcon?:string,details?:LegendDayDetails){
  const emoji=await emojis(ctx),today=legendDay(),selected=details?.day??today;
  const first=season.seasonStart.slice(0,10);
  const number=(day:string)=>Math.round((Date.parse(day)-Date.parse(first))/86400000)+1;
  const seasonDays=Math.round((Date.parse(season.seasonEnd)-Date.parse(season.seasonStart))/86400000);
  const league=emoji.get(player.leagueTier?.name??"")||emoji.get("Legend League");
  const sword=emoji.get("clash_sword"),shield=emoji.get("shield");
  const fields:NonNullable<LegacyEmbed["fields"]>=[];
  const stats=details?{
    attacks:details.attacks.length,defenses:details.defenses.filter(hit=>!hit.automatic).length,
    attackTriples:details.attacks.filter(hit=>hit.stars===3).length,
    defenseTriples:details.defenses.filter(hit=>!hit.automatic&&hit.stars===3).length,
    averageOffense:details.attacks.length?details.attackTrophies/details.attacks.length:null,
    averageDefense:details.defenses.length?details.defenseTrophies/details.defenses.length:null,
  }:season.stats;
  const offense=details?.attackTrophies??Math.round((stats.averageOffense??0)*stats.attacks);
  const defense=details?.defenseTrophies??Math.round((stats.averageDefense??0)*stats.defenses);
  const defenseCount=details?.defenses.length??stats.defenses;
  const average=(value:number|null)=>value===null?"—":signed(Number(value.toFixed(1)));
  if(!details){
    // Use calendar capacity through today's Legend day, not the number of
    // tracked rows: missing observations must not shrink the denominator.
    const possible=Math.max(0,Math.min(number(today),seasonDays))*8;
    fields.push(
      {name:`Attacks (${stats.attacks}/${possible})`,value:`-# **${signed(offense)}** (${average(stats.averageOffense)} average)\n\u200b`,inline:true},
      {name:`Defenses (${defenseCount}/${possible})`,value:`-# **${signed(defense)}** (${average(stats.averageDefense)} average)\n\u200b`,inline:true},
    );
    // 22 monospace columns, no closing-cup column: remain readable on narrow
    // Discord clients rather than relying on desktop-only inline field layout.
    let table="Day  Off   Def   Net\n";
    for(const day of days){
      // Color only net, and reset after every cell. Preserve the sign so the
      // value remains meaningful on clients that do not render ANSI colors.
      const net=signed(day.trophies).padStart(5);
      const coloredNet=day.trophies===0?net:`\u001b[${day.trophies>0?32:31}m${net}\u001b[0m`;
      const line=`${String(number(day.day)).padStart(2)} ${signed(day.attackTrophies).padStart(5)} ${signed(day.defenseTrophies).padStart(5)} ${coloredNet}\n`;
      if(table.length+line.length>900){fields.push({name:"\u200b",value:`\`\`\`ansi\n${table}\`\`\``,inline:false});table="Day  Off   Def   Net\n";}
      table+=line;
    }
    fields.push({name:"\u200b",value:days.length?`\`\`\`ansi\n${table}\`\`\``:"No recorded days yet.",inline:false});
  }
  if(details){
    const hits=(items:LegendDayBattle[],icon:string)=>items.length?items.slice(0,8).map(hit=>{
      if(hit.automatic)return `${icon} **${signed(hit.trophies)}** Auto`;
      const time=hit.time?Date.parse(hit.time):NaN;
      return `${icon} **${signed(hit.trophies)}**${Number.isFinite(time)?` <t:${Math.floor(time/1000)}:R>`:""}`;
    }).join("\n")+(items.length>8?`\n+${items.length-8} more recorded hits`:""):"None recorded yet.";
    // Keep each summary and its hit list in the same field. Only this pair is
    // inline, so Discord cannot put a third summary into the battle-list row.
    fields.push(
      // A nonempty invisible line preserves the gap when Discord stacks the
      // two inline columns on mobile; trailing newlines alone can be trimmed.
      {name:`Attacks (${stats.attacks}/8)`,value:`-# **${signed(offense)}** (${average(stats.averageOffense)} average)\n${hits(details.attacks,sword)}\n\u200b`,inline:true},
      {name:`Defenses (${defenseCount}/8)`,value:`-# **${signed(defense)}** (${average(stats.averageDefense)} average)\n${hits(details.defenses,shield)}\n\u200b`,inline:true},
    );
  }
  const armyLabel=(name:string)=>name.split(" / ").map(part=>`${emoji.get(part)} ${part}`.trim()).join(" / ");
  if(details?.topArmy)fields.push({name:"Most used army",value:`**${armyLabel(details.topArmy.name)}**`,inline:false});
  // Never mix season-wide army totals into the selected day's statistics.
  if(!details&&season.armyGroups?.length)fields.push({name:"Most used armies · season",value:season.armyGroups.slice(0,2).map(group=>{
    const label=armyLabel(group.name);
    return `**${label}**\n${group.attacks} attacks · ${percent(group.triples,group.attacks)} triples`;
  }).join("\n"),inline:false});
  // Yesterday is anchored to the current Legend day, not the selected page.
  // Keep all three destinations visible, with distinct IDs even when disabled.
  const id=(view:"day"|"season",day:string,control:number)=>["ck","page","ls",invokingUserId(ctx),player.tag,view,day,String(control)].join(":");
  const yesterday=shiftDay(today,-1);
  const components=[actionRow(
    {type:2,style:2,label:"Today",custom_id:id("day",today,1),disabled:!!details&&selected===today},
    {type:2,style:2,label:"Yesterday",custom_id:id("day",yesterday,0),disabled:today<=first||(!!details&&selected===yesterday)},
    {type:2,style:2,label:"Season",custom_id:id("season",selected,3),disabled:!details},
  )];
  const start=new Date(season.seasonStart),end=new Date(season.seasonEnd);
  // Season dates come from UTC boundaries, regardless of the Bot host timezone.
  const dateLabel=(date:Date,year:boolean)=>date.toLocaleDateString("en-US",{month:"short",day:"numeric",...(year?{year:"numeric" as const}:{}),timeZone:"UTC"});
  const seasonDates=`${dateLabel(start,start.getUTCFullYear()!==end.getUTCFullYear())} – ${dateLabel(end,true)}`;
  const response=legacyMessage({allowed_mentions:{parse:[]},components,embeds:[{
    author:{name:`${player.name}${player.clan?` | ${player.clan.name}`:""}`.slice(0,256),url:playerUrl(player.tag),...(player.clan?.badgeUrls?.small?{icon_url:player.clan.badgeUrls.small}:{})},
    title:details?"Legend Day":"Legend Season",url:playerAppUrl(player.tag,ctx.env.APP_ENV),
    description:`**${league} ${player.trophies?.toLocaleString("en")??"—"}**${player.globalRank?` · ${emoji.get("earth")} #${player.globalRank.toLocaleString("en")}`:""}${details?` · **${signed(details.trophies)} net**`:""}\n[Player profile](${playerUrl(player.tag)}) · [ClashKing](${playerAppUrl(player.tag,ctx.env.APP_ENV)})`,
    ...(townHallIcon?{thumbnail:{url:townHallIcon}}:{}),fields,color:await serverEmbedColor(ctx),
    footer:{text:details?`Day ${number(selected)}/${seasonDays}`:seasonDates},
    ...(details&&days.length?{image:{url:"attachment://legend-season.png"}}:{}),
  }]});
  const favoriteIcons=Object.fromEntries((season.favorites??[]).flatMap(item=>{const icon=emoji.component(item.name);return icon?[[item.id,`https://cdn.discordapp.com/emojis/${icon.id}.png`]]:[];}));
  if(details&&days.length){
    // Load rendering assets only for a rendered day reply, not when command
    // registration/validation imports the command definitions in plain Node.
    const {legendPoster}=await import("./legend-poster");
    response.data!.__files=[{name:"legend-season.png",bytes:await legendPoster({player,season,days,selectedDay:selected,today,townHallIcon,favoriteIcons})}];
  }
  // A message edit must explicitly remove the previous day's attachment;
  // omitting image/attachments alone leaves the old graphic on Discord.
  else response.data!.attachments=[];
  return response;
}
