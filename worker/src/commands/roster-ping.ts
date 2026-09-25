import { actionRow, legacyMessage } from "../discord/components";
import { resolveLocale, translate } from "../localization/catalog";
import { CommandInputError, invokingUserId, requireGuildId } from "./command-utils";
import { loadRoster, type Roster } from "./roster";
import type { CommandContext } from "./types";

type Target = { tag: string; name: string; userId: string | null };
const clean = (value: string) => value.replace(/[\\`*_~|<>[\]\r\n@]/g, " ").slice(0, 50);
const fail = (ctx: CommandContext) => new CommandInputError(translate("roster.pingChanged", ctx.locale));

async function targets(ctx: CommandContext, roster: Roster, mode: string): Promise<Target[]> {
  const guild = requireGuildId(ctx);
  let players = roster.members.map(m => ({ tag: m.playerTag, name: m.playerName }));
  if (mode !== "all") {
    const clans = await ctx.services.api.get<Array<{ tag: string }>>(`/v2/server/${guild}/clans-basic`);
    if (!roster.clanTag || !clans.some(c => c.tag === roster.clanTag)) {
      throw new CommandInputError(translate("roster.pingClan", ctx.locale));
    }
    // This active endpoint fetches live clan snapshots through the API's Clash client.
    const { members } = await ctx.services.api.get<{ members: Array<{ tag: string; name: string; clan_tag: string }> }>(`/v2/roster/server/${guild}/members`);
    const clan = members.filter(m => m.clan_tag === roster.clanTag);
    const rosterTags = new Set(players.map(p => p.tag));
    const clanTags = new Set(clan.map(p => p.tag));
    players = mode === "missing" ? players.filter(p => !clanTags.has(p.tag)) : clan.filter(p => !rosterTags.has(p.tag));
  }
  const links = new Map<string, string>();
  let offset = 0;
  for (;;) {
    const page = await ctx.services.api.get<{ members: Array<{ user_id: string; linked_accounts: Array<{ player_tag: string }> }>; filtered_members: number }>(
      `/v2/links/server/${guild}`, { limit: 200, offset });
    for (const member of page.members) {
      if (/^\d{17,20}$/.test(member.user_id)) for (const account of member.linked_accounts) links.set(account.player_tag, member.user_id);
    }
    offset += page.members.length;
    if (offset >= page.filtered_members) break;
    if (!page.members.length || offset >= 10000) throw fail(ctx); // Never ping from an incomplete lookup.
  }
  return [...new Map(players.map(p => [p.tag, { tag: p.tag, name: p.name, userId: links.get(p.tag) ?? null }])).values()]
    .sort((a, b) => a.tag.localeCompare(b.tag));
}

async function signature(ctx: CommandContext, id: string, mode: string, expires: string, message: string, rows: Target[]) {
  if (!ctx.env.DISCORD_BOT_TOKEN) throw fail(ctx);
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(ctx.env.DISCORD_BOT_TOKEN), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const bytes = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(JSON.stringify([
    "roster-ping-v1", requireGuildId(ctx), ctx.interaction.channel_id, invokingUserId(ctx), id, mode, expires, message, rows,
  ])));
  return [...new Uint8Array(bytes)].slice(0, 12).map(n => n.toString(16).padStart(2, "0")).join("");
}

export async function previewRosterPing(ctx: CommandContext, roster: Roster, mode: string, message: string) {
  if (message.length > 500 || !ctx.interaction.channel_id) throw fail(ctx);
  const rows = await targets(ctx, roster, mode);
  if (!rows.length) return legacyMessage({ content: translate("roster.empty", ctx.locale) }, { ephemeral: true });
  const expires = String(Math.floor(Date.now() / 1000) + 90);
  const sig = await signature(ctx, roster.id, mode, expires, message, rows);
  const users = new Set(rows.flatMap(r => r.userId ? [r.userId] : []));
  return legacyMessage({
    content: `**${clean(roster.alias)} · ${translate(`roster.${mode as "all" | "missing" | "outside"}`, ctx.locale)}**\n${translate("roster.pingPreview", ctx.locale, { players: rows.length, users: users.size })}\n\n${rows.slice(0, 10).map(r => `${clean(r.name)} (${clean(r.tag)})${r.userId ? ` · <@${r.userId}>` : " · —"}`).join("\n")}${rows.length > 10 ? "\n…" : ""}`,
    embeds: message ? [{ description: message }] : [], allowed_mentions: { parse: [] },
    components: [actionRow({ type: 2, style: 1, label: translate("roster.sendPing", ctx.locale),
      custom_id: `ck:roster:ping-send:${roster.id}:${mode}:${expires}:${sig}` })],
  }, { ephemeral: true });
}

export async function confirmRosterPing(ctx: CommandContext, parts: string[]) {
  const [, , , id, mode, expires, sig] = parts;
  if (parts.length !== 7 || !/^[0-9a-f-]{36}$/i.test(id ?? "") || !["all", "missing", "outside"].includes(mode ?? "")
    || !/^\d{10}$/.test(expires ?? "") || !/^[0-9a-f]{24}$/.test(sig ?? "")
    || Number(expires) < Date.now() / 1000 || Number(expires) > Date.now() / 1000 + 90) throw fail(ctx);
  const roster = await loadRoster(ctx, id!);
  const rows = await targets(ctx, roster, mode!);
  const message = ctx.interaction.message?.embeds?.[0]?.description ?? "";
  const expected = await signature(ctx, id!, mode!, expires!, message, rows);
  let difference = 0;
  for (let i = 0; i < expected.length; i++) difference |= expected.charCodeAt(i) ^ sig!.charCodeAt(i);
  if (difference !== 0) throw fail(ctx);
  const locale = resolveLocale(ctx.interaction.guild_locale);
  const prefix = `**${clean(roster.alias)} · ${translate(`roster.${mode as "all" | "missing" | "outside"}`, locale)}**\n${message ? `${message}\n` : ""}`;
  const mentioned = new Set<string>();
  const chunks: Array<{ content: string; users: string[] }> = [];
  let chunk = { content: prefix, users: [] as string[] };
  for (const row of rows) {
    const user = row.userId && !mentioned.has(row.userId) ? row.userId : null;
    const line = `${clean(row.name)} (${clean(row.tag)})${user ? ` · <@${user}>` : ""}\n`;
    if (chunk.content.length + line.length > 1900 || chunk.users.length >= 100) { chunks.push(chunk); chunk = { content: prefix, users: [] }; }
    chunk.content += line;
    if (user) { chunk.users.push(user); mentioned.add(user); }
  }
  chunks.push(chunk);
  for (const [i, payload] of chunks.entries()) {
    await ctx.services.discordRest.request(`/channels/${ctx.interaction.channel_id}/messages`, {
      method: "POST", body: JSON.stringify({ content: payload.content, allowed_mentions: { parse: [], users: payload.users },
        nonce: `${sig!.slice(0, 19)}:${i}`, enforce_nonce: true }),
    });
  }
  // Remove the original confirmation control. Nonces also protect concurrent clicks.
  if (ctx.interaction.message?.id) await ctx.services.discordRest.request(
    `/webhooks/${ctx.interaction.application_id}/${ctx.interaction.token}/messages/${ctx.interaction.message.id}`,
    { method: "PATCH", body: JSON.stringify({ components: [] }) });
  return legacyMessage({ content: translate("roster.pingSent", ctx.locale) }, { ephemeral: true });
}
