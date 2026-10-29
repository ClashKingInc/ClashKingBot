import { clanSelector, type ClanChoice } from "./clan-selector";
import { CommandInputError, invokingUserId } from "./command-utils";
import { InteractionResponseType, InteractionType, MessageFlags, type DiscordInteractionResponse } from "../discord/types";
import type { CommandContext } from "./types";

type Row = { type: number; components?: Array<{ type: number; custom_id?: string }> };
const selectorId = "ck:clans:select";
const pageKinds = new Set(["cl", "ca", "cg", "sc", "uc", "cr", "wp"]);
function anchor(rows: Row[]): { id: string; tag: string; member: boolean } | undefined {
  for (const row of rows) for (const control of row.components ?? []) {
    const id = control.custom_id ?? "", parts = id.split(":");
    if (parts[0] === "ck" && parts[1] === "page" && pageKinds.has(parts[2] ?? "") && /^#[0289PYLQGRJCUV]+$/u.test(parts[4] ?? ""))
      return { id, tag: parts[4]!, member: false };
    if (id.startsWith("ck:members:clan|")) {
      const values = id.slice("ck:members:".length).split("|");
      if (/^#[0289PYLQGRJCUV]+$/u.test(values[1] ?? "")) return { id, tag: values[1]!, member: true };
    }
  }
  return undefined;
}
async function linked(ctx: CommandContext) {
  if (!ctx.interaction.guild_id || !ctx.interaction.member || !invokingUserId(ctx)) return [];
  const rows = await ctx.services.api.get<ClanChoice[]>(`/v2/server/${ctx.interaction.guild_id}/clans-basic`, {}, AbortSignal.timeout(3000));
  return [...new Map(rows.filter(row => /^#[0289PYLQGRJCUV]+$/u.test(row.tag)).map(row => [row.tag, row])).values()];
}
export async function withClanSelector(ctx: CommandContext, response: DiscordInteractionResponse): Promise<DiscordInteractionResponse> {
  const rows = (response.data?.components ?? []) as Row[];
  const current = anchor(rows);
  if (!current || rows.some(row => row.components?.some(item => item.custom_id === selectorId))) return response;
  // A picker is a convenience, not a dependency of the report itself.
  const clans = await linked(ctx).catch(() => []);
  if (!clans.length || clans.length === 1 && clans[0]?.tag === current.tag) return response;
  const ordered = [...clans].sort((a, b) => a.name.localeCompare(b.name) || a.tag.localeCompare(b.tag));
  const selectedPage = Math.floor(Math.max(0, ordered.findIndex(clan => clan.tag === current.tag)) / 23);
  const page = clanSelector({ clans, selectedTag: current.tag, page: selectedPage, customId: selectorId });
  return { ...response, data: { ...response.data, components: [...rows.filter(row => !row.components?.some(item => item.custom_id === selectorId)), page.row].slice(0, 5) } };
}
export async function dispatchClanControl(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  if (ctx.interaction.data?.custom_id !== selectorId || ctx.interaction.type !== InteractionType.MessageComponent || ctx.interaction.data?.component_type !== 3 || ctx.interaction.data.values?.length !== 1)
    throw new CommandInputError("Choose a clan from this report.");
  const rows = (ctx.interaction.message?.components ?? []) as Row[], current = anchor(rows);
  if (!current) throw new CommandInputError("Refresh this report before changing clans.");
  const value = ctx.interaction.data.values[0]!;
  const run = async () => {
    // Re-read links for the clicking member. A deleted family link must not
    // remain selectable just because it was in an old Discord message.
    const clans = await linked(ctx);
    if (!clans.length) throw new CommandInputError("No clans are linked to this server.");
    if (/^page:\d{1,4}$/u.test(value)) {
      const page = clanSelector({ clans, selectedTag: current.tag, page: Number(value.slice(5)), customId: selectorId });
      return { type: InteractionResponseType.UpdateMessage, data: { components: [...rows.filter(row => !row.components?.some(item => item.custom_id === selectorId)), page.row] } };
    }
    if (!clans.some(clan => clan.tag === value)) throw new CommandInputError("That clan is no longer linked to this server.");
    let id: string;
    if (current.member) {
      const parts = current.id.slice("ck:members:".length).split("|"); parts[1] = value; id = "ck:members:" + parts.join("|");
      const { dispatchMemberReport } = await import("./member-reports");
      return { ...(await dispatchMemberReport({ ...ctx, interaction: { ...ctx.interaction, data: { ...ctx.interaction.data, custom_id: id } } })), type: InteractionResponseType.UpdateMessage };
    }
    const parts = current.id.split(":"); parts[4] = value; id = parts.join(":");
    // Reuse the existing validated state decoder so season, filters and order
    // survive the switch without maintaining a second set of option defaults.
    const { dispatchGamePage } = await import("./game-pages");
    return dispatchGamePage({ ...ctx, interaction: { ...ctx.interaction, data: { ...ctx.interaction.data, custom_id: id } } });
  };
  if (!waitUntil) return run();
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {})).catch(error =>
    ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token, { content: error instanceof CommandInputError ? error.message : "Couldn't switch clans. Please try again.", flags: MessageFlags.Ephemeral })));
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
