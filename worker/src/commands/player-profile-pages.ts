import { actionRow, legacyMessage } from "../discord/components";
import type { ApplicationEmojis } from "../discord/emojis";
import { invokingUserId, stringOption } from "./command-utils";
import { compact, escapeMarkdown, playerAppUrl, playerUrl, type Player, type LinkedAccount } from "./game-common";
import { playerOverviewReply } from "./player-profile";
import { playerCatalog, playerUpgrades, upgradeCompletion } from "./player-catalog";
import { serverEmbedColor } from "./embed-color";
import { rankedOverview } from "./ranked";
import { clashKingHistory, clashOfStatsHistory } from "./player-clan-history";
import type { CommandContext } from "./types";

interface Field {name:string;value:string;inline:boolean}
interface Embed {author?:{name:string;url?:string;icon_url?:string};title?:string;description?:string;fields?:Field[];footer?:{text:string};thumbnail?:{url:string};color?:number}
const views=[{value:"overview",label:"Overview",icon:"xp"},{value:"troops",label:"Troops",icon:"troop"},{value:"upgrades",label:"Progress",icon:"clock"},{value:"history",label:"Clan History",icon:"clan_castle"}] as const;
const labels:Record<string,string>={troops:"Troops",spells:"Spells",heroes:"Heroes",pets:"Pets",equipment:"Equipment",siege:"Siege machines"};
const duration=(seconds:number)=>{const days=Math.floor(seconds/86400),hours=Math.floor(seconds%86400/3600);return `${days?`${days}d `:""}${hours}h`;};

export async function playerProfileReply(ctx:CommandContext,player:Player,emoji:ApplicationEmojis){
 const requested=stringOption(ctx,"__view")??"overview";
 const cos=requested==="history-cos",selected=cos?"history":requested;
 if(!views.some(view=>view.value===selected))throw Error("Invalid profile page");
 let embed:Embed;
 if(selected==="overview"){
  const response=await playerOverviewReply(ctx,player,emoji);
  embed=(response.data!.embeds as Embed[])[0]!;
  await addOverviewDetails(ctx,player,emoji,embed);
 }else{
  embed={author:{name:player.name,url:playerUrl(player.tag)},title:views.find(view=>view.value===selected)!.label,
   description:`[Player profile](${playerUrl(player.tag)}) · [ClashKing](${playerAppUrl(player.tag,ctx.env.APP_ENV)})`,
   thumbnail:{url:`https://assets.clashk.ing/buildings/home-village/town_hall/level_${player.townHallLevel}.webp`},color:await serverEmbedColor(ctx),fields:[]};
  if(selected==="history"){
   const history=await (cos?clashOfStatsHistory(ctx,player):clashKingHistory(ctx,player));
   embed={title:`${player.name} Clan History`,description:history.description,color:0x2ecc71,footer:{text:history.footer}};
  }else{
   const catalog=await playerCatalog(),items=playerUpgrades(player,catalog);
   if(selected==="troops"){
    const groups=[
     {name:"Elixir troops",category:"troops",resource:"Elixir"},
     {name:"Dark Elixir troops",category:"troops",resource:"Dark Elixir"},
     {name:"Spells",category:"spells"},{name:"Heroes",category:"heroes"},{name:"Pets",category:"pets"},
     {name:"Common equipment",category:"equipment",rarity:"Common"},
     {name:"Epic equipment",category:"equipment",rarity:"Epic"},{name:"Siege machines",category:"siege"},
    ];
    for(const group of groups){
     const units=items.filter(item=>item.category===group.category&&item.current>0&&(!group.resource||item.resource===group.resource)&&(!group.rarity||item.rarity===group.rarity));
     const width=group.category==="heroes"?3:2,perRow=group.category==="heroes"?2:3;
     // Pad outside the pair, keeping digits adjacent to the centered slash.
     // Nonbreaking spaces survive inline-code edge trimming. Heroes need
     // three digits per side and fewer columns on mobile.
     const rows:string[]=[];
     for(let i=0;i<units.length;i+=perRow)rows.push(units.slice(i,i+perRow).map(item=>`${emoji.get(item.name)||escapeMarkdown(item.name)} \`${String(item.current).padStart(width,"\u00a0")}/${String(item.maximum).padEnd(width,"\u00a0")}\``).join("  "));
     if(rows.length)embed.fields!.push({name:group.name,value:rows.join("\n"),inline:false});
    }
    const builder=[...(player.heroes??[]),...(player.troops??[])].filter(unit=>unit.village==="builderBase");
    if(builder.length)embed.fields!.push({name:"Builder Base",value:builder.map(unit=>`${emoji.get(unit.name)||escapeMarkdown(unit.name)} \`${unit.level}${unit.maxLevel?`/${unit.maxLevel}`:""}\``).join("  "),inline:false});
   }else{
    const global=playerUpgrades(player,catalog,Number.MAX_SAFE_INTEGER);
    const percent=(done:number,total:number)=>total?`${(100*done/total).toFixed(1)}%`:"—";
    const completion=(units:typeof items)=>{const value=upgradeCompletion(units);return value===undefined?"—":`${(value*100).toFixed(1)}%`;};
    const maxTownHall=Math.max(0,...(catalog.get("buildings")?.find(item=>item.name==="Town Hall")?.levels.map(level=>level.level)??[]));
    const atGameMax=maxTownHall>0&&player.townHallLevel>=maxTownHall;
    const deficit=(units:typeof items)=>units.reduce((sum,item)=>sum+Math.max(0,item.previous-item.current),0);
    const costs:Record<string,number>={};for(const item of items)for(const [resource,value] of Object.entries(item.costs))costs[resource]=(costs[resource]??0)+value;
    const missing=items.reduce((sum,item)=>sum+Math.max(0,item.maximum-item.current),0);
    embed.fields!.push({name:"Overall progress",value:`${atGameMax?`**${completion(items)}** to max`:`**${completion(items)}** of TH${player.townHallLevel} max\n**${completion(global)}** of game max`}\n**${missing}** levels left\n**${deficit(items)}** levels behind TH${player.townHallLevel-1}`,inline:false});
    embed.fields!.push({name:`${emoji.get(player.townHallLevel)} Remaining at TH${player.townHallLevel}`,value:`${emoji.get("clock")} **${duration(items.reduce((sum,item)=>sum+item.seconds,0))}** upgrade work\n${resourceCosts(costs,emoji)}`,inline:false});
    const categoryIcons:Record<string,string>={troops:"Barbarian",spells:"Rage Spell",heroes:"Barbarian King",pets:"Unicorn",equipment:"Giant Gauntlet",siege:"Wall Wrecker"};
    for(const category of Object.keys(labels)){
     const units=items.filter(item=>item.category===category);
     const globalUnits=global.filter(item=>item.category===category);
     if(!units.length)continue;
     const baseline=units.reduce((sum,item)=>sum+item.previous,0);
     const behind=deficit(units);
     const categoryCosts:Record<string,number>={};for(const item of units)for(const [resource,value] of Object.entries(item.costs))categoryCosts[resource]=(categoryCosts[resource]??0)+value;
     embed.fields!.push({name:`${emoji.get(categoryIcons[category]!)} ${labels[category]!}`.trim(),value:`${atGameMax?`**${completion(units)}** to max`:`**${completion(units)}** TH max / **${completion(globalUnits)}** game max`}\n${behind?`**${percent(behind,baseline)}** rushed (${behind} levels behind)`:"Not rushed"}${category!=="equipment"?`\n${emoji.get("clock")} ${duration(units.reduce((sum,item)=>sum+item.seconds,0))} remaining`:""}\n${resourceCosts(categoryCosts,emoji)}`,inline:false});
    }
   }
  }
 }
 const troopPages:string[]=[];
 if(selected==="troops"){
  const intro=embed.description??"",budget=4096-intro.length-2;
  let body="";
  // Description pages have a larger budget than fields. Preserve whole groups
  // where possible and only split oversized groups between complete rows.
  for(const field of embed.fields??[]){
   const heading=`**${field.name}**\n`,section=heading+field.value;
   if(section.length<=budget){
    if(body&&body.length+section.length+2>budget){troopPages.push(intro+"\n\n"+body);body="";}
    body+=(body?"\n\n":"")+section;
   }else{
    if(body){troopPages.push(intro+"\n\n"+body);body="";}
    body=heading;
    for(const row of field.value.split("\n")){
     if(body.length+row.length+1>budget){troopPages.push(intro+"\n\n"+body.trimEnd());body=heading;}
     body+=(body===heading?"":"\n")+row;
    }
   }
  }
  if(body)troopPages.push(intro+"\n\n"+body);
 }
 const chunks:Field[]=[];
 for(const field of selected==="troops"?[]:embed.fields??[]){
  let value="";
  // Split long fields only at a space/line boundary, never through an emoji ID.
  for(const word of field.value.split(/(?<=\s)/u)){
   if(value.length+word.length>1000){chunks.push({...field,value:value.trimEnd()+"\n\u200b"});value="";}
   value+=word;
  }
  // Discord trims empty trailing lines. A zero-width space keeps the final
  // blank line visible when fields stack on mobile, including split fields.
  if(value)chunks.push({...field,value:value.trimEnd()+"\n\u200b"});
 }
 const pages:Field[][]=[[]];let size=0;
 for(const field of chunks){if(size+field.value.length+field.name.length>4800||pages.at(-1)!.length>=25){pages.push([]);size=0;}pages.at(-1)!.push(field);size+=field.value.length+field.name.length;}
 const pageCount=selected==="troops"?Math.max(1,troopPages.length):pages.length;
 const raw=Number(ctx.options.get("__page")?.value??0),page=Math.max(0,Math.min(Number.isSafeInteger(raw)?raw:0,pageCount-1));
 if(selected==="troops"){embed.description=troopPages[page]??embed.description;delete embed.fields;}
 else if(selected==="history")delete embed.fields;
 else embed.fields=pages[page];
 // Keep separation between fields, but never pad the bottom of an embed.
 const lastField=embed.fields?.at(-1);if(lastField)lastField.value=lastField.value.replace(/\n\u200b$/u,"");
 if(selected!=="history")embed.footer={text:`${player.tag}${selected==="upgrades"?" · Rushed = missing levels from the previous Town Hall":""}${pageCount>1?` · Page ${page+1}/${pageCount}`:""}`};
 const accountsUser=stringOption(ctx,"__accounts_user")??stringOption(ctx,"discord_user")??"none";
 const owner=invokingUserId(ctx),id=(view:string,index:number)=>`ck:page:pp:${owner}:${player.tag}:${view}:${accountsUser}:${index}`;
 const components=[actionRow({type:3,custom_id:id("select",0),placeholder:"Choose a page",min_values:1,max_values:1,
  options:views.map(view=>{const icon=emoji.component(view.icon);return {label:view.label,value:view.value,default:view.value===selected,...(icon?{emoji:{id:icon.id,name:icon.name}}:{})};})})];
 if(selected==="history")components.push(actionRow(
  {type:2,style:2,label:"ClashKing",custom_id:id("history",0),disabled:!cos},
  {type:2,style:2,label:"Clash of Stats",custom_id:id("history-cos",0),disabled:cos},
 ));
 if(accountsUser!=="none"){
  const accounts=await ctx.services.api.get<{items:LinkedAccount[]}>(`/v2/links/${accountsUser}`);
  const visible=accounts.items.filter(account=>!account.hidden).slice(0,25);
  if(visible.length>1)components.push(actionRow({type:3,custom_id:id("account",0),placeholder:"Choose an account",min_values:1,max_values:1,options:visible.map(account=>({label:(account.player_name??account.player_tag).slice(0,100),description:account.player_tag,value:account.player_tag,default:account.player_tag===player.tag}))}));
 }
 if(pageCount>1)components.push(actionRow({type:2,style:2,label:"Previous",custom_id:id(selected,page-1),disabled:page===0},{type:2,style:2,label:"Next",custom_id:id(selected,page+1),disabled:page===pageCount-1}));
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[embed],components});
}
function resourceCosts(costs:Record<string,number>,emoji:ApplicationEmojis){return Object.entries(costs).filter(([,value])=>value>0).map(([resource,value])=>{const key=resource.replace(/([a-z])([A-Z])/gu,"$1_$2").toLowerCase().replaceAll(" ","_");return `${emoji.get(key)||emoji.get(key.replaceAll("_",""))||escapeMarkdown(resource.replaceAll("_"," "))} ${compact(value)}`;}).join(" · ")||"No upgrades remaining";}

async function addOverviewDetails(ctx:CommandContext,player:Player,emoji:ApplicationEmojis,embed:Embed){
 const fields=embed.fields??=[];
 const encoded=encodeURIComponent(player.tag);
 const now=new Date(),after=new Date(now.getTime()-30*86400000);
 const [season,war,bans,identity,ranked]=await Promise.allSettled([
  ctx.services.api.get<{recordedBattles:number;gold:number;elixir:number;darkElixir:number;statObservations:number;clanGames:number;capitalDonated:number}>(`/v2/bot/players/${encoded}/season-stats`),
  ctx.services.api.get<{items:Array<{attacksPerMember:number;attacks:Array<{stars:number;destructionPercentage:number}>}>}>(`/v2/player/${encoded}/war/stats`,{limit:500,"time[after]":after.toISOString(),"time[before]":now.toISOString()}),
  ctx.interaction.guild_id?ctx.services.api.get<{items:Array<{VillageTag:string;Notes:string;DateCreated:string}>}>(`/v2/server/${ctx.interaction.guild_id}/bans`):Promise.resolve({items:[]}),
  ctx.services.api.get<{link:{userId:string;verified:boolean}|null;lastObservedAt:string|null}>(`/v2/bot/players/${encoded}/identity`,ctx.interaction.guild_id?{serverId:ctx.interaction.guild_id}:{}),
  rankedOverview(ctx,player),
 ]);
 if(ranked.status==="fulfilled"&&ranked.value){
  const r=ranked.value,field=fields[0]!;
  const count=(value:number)=>`${value}${r.limit?`/${r.limit}`:""}`;
  field.value+=`\n• Rank **#${r.rank}**\n• ${count(r.attacks)} attacks\n• ${count(r.defenses)} defenses`;
 }
 if(identity.status==="fulfilled"){
  const {link,lastObservedAt}=identity.value;
  const details=[];
  if(link)details.push(`${emoji.get(link.verified?"account_verified":"account_unverified")} <@${link.userId}>`);
  if(lastObservedAt)details.push(`Last seen <t:${Math.floor(Date.parse(lastObservedAt)/1000)}:R>`);
  if(details.length)embed.description+=`\n${details.join("\n")}`;
 }
 if(season.status==="fulfilled"){
  const s=season.value;
  const stats=fields.find(field=>field.name==="Season stats");
  if(s.recordedBattles&&stats)stats.value+=`\n${emoji.get("gold")} ${compact(s.gold)} · ${emoji.get("elixir")} ${compact(s.elixir)} · ${emoji.get("dark_elixir")} ${compact(s.darkElixir)}`;
 }
 if(war.status==="fulfilled"){
  const attacks=war.value.items.flatMap(item=>item.attacks);
  const missed=war.value.items.reduce((sum,item)=>sum+Math.max(0,item.attacksPerMember-item.attacks.length),0);
  if(war.value.items.length)fields.push({name:"War (Last 30 days)",value:`${emoji.get("clash_sword")} **${attacks.length}** attacks (**${missed}** missed)\n${emoji.get("war_star")} **${attacks.reduce((sum,hit)=>sum+hit.stars,0)}** stars (**${attacks.length?(attacks.reduce((sum,hit)=>sum+hit.stars,0)/attacks.length).toFixed(2):"—"}** avg)\nTriples: **${attacks.length?(attacks.filter(hit=>hit.stars===3).length/attacks.length*100).toFixed(1)+"%":"—"}**`,inline:false});
 }
 if(bans.status==="fulfilled")for(const ban of bans.value.items.filter(item=>item.VillageTag===player.tag))fields.push({name:"Banned player",value:`${escapeMarkdown(ban.Notes||"No reason given")}\n${escapeMarkdown(ban.DateCreated)}`,inline:false});
}
