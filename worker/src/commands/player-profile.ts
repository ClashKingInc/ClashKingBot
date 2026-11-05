import { actionRow, legacyMessage } from "../discord/components";
import type { ApplicationEmojis } from "../discord/emojis";
import { invokingUserId, stringOption } from "./command-utils";
import { serverEmbedColor } from "./embed-color";
import { compact, escapeMarkdown, fetchPlayer, pagedGameReply, playerAppUrl, playerLabel, playerUrl, type LinkedAccount, type Player } from "./game-common";
import type { CommandContext } from "./types";

const safeName=(value:string)=>`\u2068${escapeMarkdown(value.replace(/[\u202a-\u202e\u2066-\u2069]/gu,""))}\u2069`;
const hall=(level:number)=>`https://assets.clashk.ing/buildings/home-village/town_hall/level_${level}.webp`;
export async function playerOverviewReply(ctx:CommandContext,player:Player,emoji:ApplicationEmojis){
 const metric=(icon:string,value:number|undefined,label:string)=>value===undefined?"":`${emoji.get(icon)} **${compact(value)}** ${label}`;
 const role=({admin:"Co-Leader",coleader:"Co-Leader",leader:"Leader",elder:"Elder",member:"Member"} as Record<string,string>)[(player.role??"").replaceAll("-","").toLowerCase()];
 const clan=player.clan?`${safeName(player.clan.name)}${role?` (${role})`:""}`:"No clan";
 // Discord mobile has narrow embeds, especially beside a thumbnail. Keep each
 // labelled metric on its own line instead of relying on desktop-width wrapping.
 const fields=[
  {name:player.leagueTier?.name??"Season",value:[metric(player.leagueTier?.name??"trophy",player.trophies,"trophies"),...(!player.currentLeagueGroupTag?[`• ${player.attackWins??0} attack wins`,`• ${player.defenseWins??0} defense wins`]:[])].filter(Boolean).join("\n"),inline:false},
  {name:"Season stats",value:`${emoji.get("up_green_arrow")} **${compact(player.donations)}** donated\n${emoji.get("down_red_arrow")} **${compact(player.donationsReceived)}** received`,inline:false},
  {name:"All time",value:[metric("war_star",player.warStars,"war stars"),metric("trophy",player.bestTrophies,"best trophies")].filter(Boolean).join("\n"),inline:false},
 ];
 return legacyMessage({allowed_mentions:{parse:[]},embeds:[{
  color:await serverEmbedColor(ctx),author:{name:player.name,url:playerUrl(player.tag),...(player.clan?.badgeUrls?.small?{icon_url:player.clan.badgeUrls.small}:{})},
  thumbnail:{url:hall(player.townHallLevel)},description:`${clan}\n[Player profile](${playerUrl(player.tag)}) · [ClashKing](${playerAppUrl(player.tag,ctx.env.APP_ENV)})`,fields,footer:{text:player.tag},
 }],components:[]});
}

export async function playerAccountsReply(ctx:CommandContext,accounts:LinkedAccount[],emoji:ApplicationEmojis){
 const rows:Array<{account:LinkedAccount;player?:Player}>=[];
 // Linked lists can be large. Do not burst every account into the proxy at once.
 for(let i=0;i<accounts.length;i+=5)rows.push(...await Promise.all(accounts.slice(i,i+5).map(async account=>({account,player:await fetchPlayer(ctx,account.player_tag).catch(()=>undefined)}))));
 rows.sort((a,b)=>(b.player?.townHallLevel??b.account.town_hall??0)-(a.player?.townHallLevel??a.account.town_hall??0)||(b.player?.trophies??0)-(a.player?.trophies??0));
 const lines=rows.map(({account,player})=>{
  const verification=emoji.get(account.is_verified?"account_verified":"account_unverified")||`(${account.is_verified?"verified":"unverified"})`;
  const identity=playerLabel({tag:account.player_tag,name:player?.name??account.player_name??account.player_tag});
  return `${emoji.get(player?.townHallLevel??account.town_hall??0)} **${verification} ${identity}**\n`
   +(player?`${emoji.get(player.leagueTier?.name??"trophy")||emoji.get("trophy")} **${player.trophies.toLocaleString("en")}**${player.clan?` · ${safeName(player.clan.name)}`:" · No clan"}`:"Player unavailable");
 });
 const target=stringOption(ctx,"discord_user")??invokingUserId(ctx);
 const response=await pagedGameReply(ctx,`${accounts.length} linked accounts`,lines,"ac",[target]);
 const embed=(response.data!.embeds as Array<Record<string,unknown>>)[0]!;
 if(lines.length<=15)delete embed.footer;
 const page=Number(ctx.options.get("__page")?.value??0);
 const refresh=emoji.component("refresh");
 response.data!.components=[...(response.data!.components as unknown[]??[]),actionRow({type:2,style:2,...(refresh?{emoji:{id:refresh.id,name:refresh.name}}:{label:"Refresh"}),custom_id:`ck:page:ac:${invokingUserId(ctx)}:${target}:${page}`})];
 return response;
}
