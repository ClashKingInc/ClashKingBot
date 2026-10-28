import { actionRow, legacyMessage } from "../discord/components";
import { applicationEmojis } from "../discord/emojis";
import { CommandInputError, invokingUserId, normalizeTag, OptionType, stringOption } from "./command-utils";
import type { ApplicationCommandOption, CommandContext } from "./types";
import type { AppEnvironment } from "../env";
import { serverEmbedColor } from "./embed-color";

export interface Player {
  name: string; tag: string; townHallLevel: number; trophies: number; warStars: number;
  expLevel: number; donations: number; donationsReceived: number;
  clan?: { name: string; tag: string; badgeUrls?: { small?: string; large?: string } }; leagueTier?: { id: number; name: string };
  league?: { id: number; name: string };
  heroes?: PlayerUnit[];
  troops?: PlayerUnit[]; spells?: PlayerUnit[]; heroEquipment?: PlayerUnit[];
  builderHallLevel?: number; clanCapitalContributions?: number;
  bestTrophies?: number; builderBaseTrophies?: number; bestBuilderBaseTrophies?: number;
  attackWins?: number; defenseWins?: number; role?: string; warPreference?: string;
  achievements?: Array<{ name: string; value: number }>;
  currentLeagueGroupTag?: string | null;
  currentLeagueSeasonId?: number | null;
}
/** Only Legend I has eight daily attacks. Lower Legend tiers use weekly Ranked
 * groups. Prefer the numeric tier over localized names and legacy league data. */
export function isDailyLegend(player: { leagueTier?: { id?: number }; league?: { id?: number } }): boolean {
  return player.leagueTier?.id ? player.leagueTier.id === 105000036 : player.league?.id === 29000022;
}
export interface PlayerUnit { name:string; level:number; maxLevel?:number; village?:string; superTroopIsActive?:boolean }
export interface LinkedAccount { player_tag: string; player_name?: string; town_hall?: number; is_verified: boolean; hidden?:boolean }
export const playerOption: ApplicationCommandOption = {
  name: "player", description: "Player tag or name", type: OptionType.String, autocomplete: true, required: true,
};
export const userOption: ApplicationCommandOption = { name: "discord_user", description: "Discord member whose linked accounts to use", type: OptionType.User };
export function subcommand(ctx: CommandContext): CommandContext {
  const selected = [...ctx.options.values()].find(option => option.type === OptionType.Subcommand);
  if (!selected) throw new CommandInputError("Choose a subcommand.");
  return { ...ctx, path: [selected.name], options: new Map((selected.options ?? []).map(option => [option.name, option])) };
}
export const escapeMarkdown = (value: string) => value.replace(/[\\`*_~|>[\]]/gu, "\\$&");
export const compact = (value: number) => new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
export const playerUrl = (tag: string) => `https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=${encodeURIComponent(tag)}`;
// Links must follow the bot environment, never send Beta users to production.
export const playerAppUrl = (tag: string, environment: AppEnvironment) =>
  `https://${environment === "dev" ? "local-app" : "app"}.clashk.ing/player/${encodeURIComponent(tag.replace(/^#/u,""))}`;
export const playerLabel = (player: { name: string; tag: string }) => `[${escapeMarkdown(player.name)}](${playerUrl(player.tag)})`;
export async function linkedAccounts(ctx: CommandContext): Promise<LinkedAccount[]> {
  const result = await ctx.services.api.get<{ items: LinkedAccount[] }>(`/v2/links/${stringOption(ctx, "discord_user") ?? invokingUserId(ctx)}`);
  return result.items;
}
export async function resolvePlayerTag(ctx: CommandContext): Promise<string> {
  const raw = stringOption(ctx, "player");
  // An omitted player must never silently choose the first linked account.
  if (!raw?.trim()) throw new CommandInputError("Choose a player or enter a player tag.");
  return normalizeTag(raw, ctx.locale);
}
export async function fetchPlayer(ctx: CommandContext, tag: string): Promise<Player> {
  return ctx.services.api.get<Player>(`/v2/bot/clash/players/${encodeURIComponent(tag)}`);
}
export async function playerAutocomplete(context: CommandContext) {
  const ctx = subcommand(context);
  const query = String(ctx.options.get("player")?.value ?? "").trim();
  if (!query) return (await linkedAccounts(ctx)).slice(0, 25).map(item => ({
    name: `${item.player_name ?? "Player"} | ${item.player_tag}`.slice(0, 100), value: item.player_tag,
  }));
  const result = await ctx.services.api.get<{ items: Array<{ name: string; tag: string }> }>("/v2/player/search", { query, limit: 25 });
  return result.items.map(item => ({ name: `${item.name} | ${item.tag}`.slice(0, 100), value: item.tag }));
}
/** Personal suggestions only: a bookmark is sufficient; an unbookmarked link
 * must be verified. Never fall back to public search for this private list. */
export async function personalPlayerAutocomplete(context: CommandContext, options:{legendsOnly?:boolean}={}) {
  const ctx=subcommand(context),userId=invokingUserId(ctx);
  const query=String(ctx.options.get("player")?.value??"").trim().toLocaleLowerCase();
  const [links,bookmarks]=await Promise.all([
    linkedAccounts(ctx),
    ctx.services.api.get<{items:Array<{tag:string}>}>(`/v2/links/${userId}/bookmarks`,{type:"player"}),
  ]);
  const eligible=new Map<string,LinkedAccount>();
  for(const account of links)if(account.is_verified)eligible.set(account.player_tag,account);
  for(const bookmark of bookmarks.items)if(!eligible.has(bookmark.tag))eligible.set(bookmark.tag,{player_tag:bookmark.tag,is_verified:false});
  const accounts=[...eligible.values()];
  // Resolve names/TH through the existing API, with bounded parallelism and a
  // short deadline so a slow game request cannot exhaust Discord autocomplete.
  const resolved: Array<{name:string;tag:string;townHall:number}>=[];
  const deadline=AbortSignal.timeout(1800);
  let index=0;
  await Promise.all(Array.from({length:Math.min(5,accounts.length)},async()=>{
    while(index<accounts.length){
      const account=accounts[index++]!;
      const player=deadline.aborted?undefined:await ctx.services.api.get<Player>(`/v2/bot/clash/players/${encodeURIComponent(account.player_tag)}`,{},deadline).catch(()=>undefined);
      // Static league tier IDs identify current Legend membership even when
      // display names are localized. A failed lookup cannot prove eligibility.
      if(options.legendsOnly&&(!player||!isDailyLegend(player)))continue;
      resolved.push({name:player?.name??account.player_name??account.player_tag,tag:account.player_tag,townHall:player?.townHallLevel??account.town_hall??0});
    }
  }));
  return resolved.sort((a,b)=>b.townHall-a.townHall||a.name.localeCompare(b.name)||a.tag.localeCompare(b.tag))
    .filter(account=>`${account.name} ${account.tag}`.toLocaleLowerCase().includes(query))
    .slice(0,25).map(account=>{
      const prefix=`(TH${account.townHall||"?"}) `,suffix=` | ${account.tag}`;
      return {name:prefix+account.name.slice(0,100-prefix.length-suffix.length)+suffix,value:account.tag};
    });
}
export async function gameReply(ctx: CommandContext, title: string, description: string, tag?: string, footer?: string) {
  const playerLink=tag?`\n\n[Open player](${playerUrl(tag)})`:"";
  return legacyMessage({ allowed_mentions: { parse: [] }, embeds: [{ color: await serverEmbedColor(ctx), title,
    ...(tag?{url:playerAppUrl(tag,ctx.env.APP_ENV)}:{}),
    description: (description || "No recorded results.").slice(0,4096-playerLink.length)+playerLink,
    ...(footer ? { footer: { text: footer } } : {}) }],components:[] });
}
export async function pagedGameReply(ctx: CommandContext, title: string, entries: string[], kind: string,
  args: string[], tag?: string, footer?: string) {
  const pages: string[][] = [[]];
  for (const entry of entries) {
    const page = pages[pages.length-1]!;
    if (page.length >= 15 || page.join("\n").length + entry.length + 1 > 3500) pages.push([]);
    pages[pages.length-1]!.push(entry);
  }
  const requested = Number(ctx.options.get("__page")?.value ?? 0);
  const page = Number.isSafeInteger(requested) ? Math.max(0,Math.min(requested,pages.length-1)) : 0;
  const response = await gameReply(ctx,title,pages[page]!.join("\n"),tag,
    [footer,`Page ${page+1}/${pages.length} · ${entries.length} entries`].filter(Boolean).join(" · "));
  if (pages.length > 1) {
    const id = (index: number) => ["ck","page",kind,invokingUserId(ctx),...args,String(index)].join(":");
    const navigation = actionRow(
      {type:2,style:2,label:"Previous",custom_id:id(page-1),disabled:page===0},
      {type:2,style:2,label:"Next",custom_id:id(page+1),disabled:page===pages.length-1});
    response.data!.components = [...(response.data!.components as unknown[] ?? []),navigation];
  }
  return response;
}
export const emojis = (ctx: CommandContext) => applicationEmojis(ctx.services.discordRest);
/** Legend days reset at 05:10 UTC, independent of the user's timezone. */
export function legendDay(now = Date.now()): string { return new Date(now - (5 * 60 + 10) * 60_000).toISOString().slice(0, 10); }
