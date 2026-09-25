import { ClashKingApiError } from "../api/client";
import { actionRow, legacyMessage, type ButtonComponent } from "../discord/components";
import { InteractionResponseType, InteractionType, type DiscordInteractionResponse } from "../discord/types";
import { localizations, resolveLocale, translate } from "../localization/catalog";
import { CommandInputError, invokingUserId, normalizeTag, requireGuildId } from "./command-utils";
import { modalFields } from "./modals";
import type { Command, CommandContext } from "./types";
import { previewRosterPing, confirmRosterPing } from "./roster-ping";

// Projections of api-contracts/src/bot-server.ts; never Dashboard's snake_case response.
interface Question { id: string; label: string; type: string; required: boolean; options: string[]; order: number }
export interface Roster {
  id: string; serverId: string; alias: string; description: string | null; memberCount: number;
  clanTag?: string | null;
  requireVerified?: boolean;
  questionnaire: { questions: Question[] };
  members: Array<{ playerTag: string; playerName: string; townhall: number; clanName: string | null }>;
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PAGE_SIZE = 15;
type Key = Parameters<typeof translate>[0];
const t = (ctx: CommandContext, key: Key) => translate(key, ctx.locale);
const reply = (content: string) => legacyMessage({ content }, { ephemeral: true });
const clean = (value: string, length: number) => value.replace(/[\\`*_~|<>[\]\r\n]/g, " ").slice(0, length);
const endpoint = (ctx: CommandContext, id = "") => `/v2/server/${requireGuildId(ctx)}/rosters${id ? `/${id}` : ""}`;
const button = (ctx: CommandContext, action: string, key: Key, id = ""): ButtonComponent => ({
  type: 2, style: 2, custom_id: `ck:roster:${action}${id ? `:${id}` : ""}`, label: t(ctx, key),
});
function manager(ctx: CommandContext): boolean {
  const raw = ctx.interaction.member?.permissions ?? "0";
  return /^\d+$/.test(raw) && (BigInt(raw) & (8n | 32n)) !== 0n;
}
function requireManager(ctx: CommandContext): void {
  if (!manager(ctx)) throw new CommandInputError(t(ctx, "roster.permission"));
}
export async function loadRoster(ctx: CommandContext, id: string, modal = false): Promise<Roster> {
  const result = await ctx.services.api.get<{ roster: Roster }>(endpoint(ctx, id), {}, AbortSignal.timeout(modal ? 1500 : 8000));
  if (result.roster.id !== id || result.roster.serverId !== requireGuildId(ctx)) throw new Error("Roster scope mismatch");
  return result.roster;
}
const load = loadRoster;
const rosterOption = { name: "roster", type: 3, description: translate("roster.title"),
  description_localizations: localizations("roster.title"), required: true, autocomplete: true };
const choice = (value: string, key: Key) => ({ value, name: translate(key), name_localizations: localizations(key) });
export const rosterCommand: Command = {
  deferred: true, ephemeral: true,
  definition: { name: "roster", type: 1, contexts: [0], integration_types: [0], default_member_permissions: "32",
    name_localizations: localizations("roster.name"), description: translate("roster.title"),
    description_localizations: localizations("roster.title"), options: [
      { name: "post", type: 1, description: translate("roster.post"), description_localizations: localizations("roster.post"), options: [rosterOption,
        { name: "type", type: 3, description: translate("roster.post"), required: true, choices: [
          choice("signup", "roster.signupMode"), choice("post", "roster.title"), choice("static", "roster.staticMode"),
        ] }] },
      { name: "ping", type: 1, description: translate("roster.ping"), description_localizations: localizations("roster.ping"), options: [rosterOption,
        { name: "type", type: 3, description: translate("roster.ping"), required: true, choices: [
          choice("missing", "roster.missing"), choice("outside", "roster.outside"), choice("all", "roster.all"),
        ] }, { name: "message", type: 3, description: translate("base.descriptionLabel"), max_length: 500 }] },
      { name: "create", type: 1, description: translate("roster.create"), description_localizations: localizations("roster.create") },
    ] },
  autocomplete: async (ctx) => {
    requireGuildId(ctx);
    const options = ctx.interaction.data?.options?.[0]?.options ?? [];
    const focused = options.find(option => option.focused);
    if (focused?.name !== "roster") return [];
    const query = String(focused.value ?? "").toLocaleLowerCase();
    const { items } = await ctx.services.api.get<{ items: Roster[] }>(endpoint(ctx), {}, AbortSignal.timeout(1500));
    return items.filter(r => r.serverId === requireGuildId(ctx) && uuid.test(r.id) && `${r.alias} ${r.clanTag ?? ""}`.toLocaleLowerCase().includes(query))
      .sort((a, b) => a.alias.localeCompare(b.alias)).slice(0, 25)
      .map(r => ({ name: `${r.alias} | ${r.clanTag ?? "—"} | 👥 ${r.memberCount}`.slice(0, 100), value: r.id }));
  },
  execute: (ctx) => guarded(ctx, async () => {
    const sub = ctx.interaction.data?.options?.[0];
    if (sub?.name === "create") return createModal(ctx);
    requireManager(ctx);
    const options = new Map(sub?.options?.map(option => [option.name, option.value]));
    const id = String(options.get("roster") ?? "");
    const mode = String(options.get("type") ?? "");
    if (!uuid.test(id)) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
    if (sub?.name === "post" && ["signup", "post", "static"].includes(mode)) return post(ctx, id, mode);
    if (sub?.name === "ping" && ["missing", "outside", "all"].includes(mode)) {
      return previewRosterPing(ctx, await load(ctx, id), mode, String(options.get("message") ?? ""));
    }
    throw new CommandInputError(t(ctx, "error.invalidInteraction"));
  }),
};

async function guarded(ctx: CommandContext, run: () => Promise<DiscordInteractionResponse>) {
  try { requireGuildId(ctx); return await run(); }
  catch (error) {
    if (error instanceof CommandInputError) return reply(error.message);
    if (error instanceof ClashKingApiError && error.status === 404) return reply(t(ctx, "roster.notFound"));
    return reply(t(ctx, "roster.failed"));
  }
}
async function list(ctx: CommandContext, page: number): Promise<DiscordInteractionResponse> {
  const { items } = await ctx.services.api.get<{ items: Roster[] }>(endpoint(ctx), {}, AbortSignal.timeout(8000));
  const sorted = [...items].sort((a, b) => a.alias.localeCompare(b.alias) || a.id.localeCompare(b.id));
  const last = Math.max(0, Math.ceil(sorted.length / PAGE_SIZE) - 1);
  page = Math.min(page, last);
  const rows = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const components = rows.length ? [actionRow({ type: 3, custom_id: "ck:roster:select", placeholder: t(ctx, "roster.view"),
    options: rows.map(r => ({ label: r.alias.slice(0, 100) || r.id, value: r.id, description: `👥 ${r.memberCount}` })) })] : [];
  const controls: ButtonComponent[] = [];
  if (page > 0) controls.push({ type: 2, style: 2, label: "←", custom_id: `ck:roster:list:${page - 1}` });
  if (page < last) controls.push({ type: 2, style: 2, label: "→", custom_id: `ck:roster:list:${page + 1}` });
  if (manager(ctx)) controls.push(button(ctx, "create", "roster.create"));
  if (controls.length) components.push(actionRow(...controls));
  return legacyMessage({ content: rows.length ? `${t(ctx, "roster.title")} · ${page + 1}/${last + 1}` : t(ctx, "roster.empty"), components }, { ephemeral: true });
}
function rosterText(ctx: CommandContext, roster: Roster, page: number): string {
  const members = roster.members.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const digits = "⁰¹²³⁴⁵⁶⁷⁸⁹";
  const lines = members.map(m => `${String(m.townhall).replace(/\d/g, n => digits[Number(n)] ?? n)}${clean(m.playerName, 30)} (${clean(m.playerTag, 15)}) | ${clean(m.clanName ?? "—", 25)}`);
  return `**${clean(roster.alias, 100)}** · 👥 ${roster.members.length}\n${clean(roster.description ?? "", 300)}\n\n${lines.join("\n") || t(ctx, "roster.empty")}\n\n${page + 1}/${Math.max(1, Math.ceil(roster.members.length / PAGE_SIZE))}`;
}
async function view(ctx: CommandContext, id: string, page = 0) {
  const roster = await load(ctx, id);
  const last = Math.max(0, Math.ceil(roster.members.length / PAGE_SIZE) - 1);
  page = Math.min(page, last);
  const controls = [button(ctx, "join", "roster.join", id)];
  if (manager(ctx)) controls.push(button(ctx, "post", "roster.post", id));
  if (page > 0) controls.push({ type: 2, style: 2, label: "←", custom_id: `ck:roster:view:${id}:${page - 1}` });
  if (page < last) controls.push({ type: 2, style: 2, label: "→", custom_id: `ck:roster:view:${id}:${page + 1}` });
  return { type: 4, data: { content: rosterText(ctx, roster, page), flags: 64, allowed_mentions: { parse: [] }, components: [actionRow(...controls)] } };
}
function createModal(ctx: CommandContext): DiscordInteractionResponse {
  return legacyMessage({ components: [actionRow({ type: 2, style: 5,
    label: t(ctx, "roster.create"), url: rosterDashboardUrl(ctx) })] }, { ephemeral: true });
}
export function rosterDashboardUrl(ctx: CommandContext, id?: string): string {
  const origin = ctx.env.DASHBOARD_BASE_URL;
  if (!origin) throw new CommandInputError(t(ctx, "roster.failed"));
  const url = new URL(id ? "/dashboard/rosters/detail" : "/dashboard/rosters", origin);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) throw new Error("Invalid Dashboard origin");
  url.searchParams.set("guildId", requireGuildId(ctx));
  if (id) url.searchParams.set("rosterId", id);
  return url.toString();
}
async function formVersion(questions: Question[]): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(questions)));
  return [...new Uint8Array(digest)].slice(0, 8).map(n => n.toString(16).padStart(2, "0")).join("");
}
function questionsFor(roster: Roster): Question[] {
  return [...roster.questionnaire.questions].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}
function supported(questions: Question[]): boolean {
  return questions.length <= 4 && questions.every(q => q.label.length > 0 && q.label.length <= 45
    && ["text", "boolean", "single_select"].includes(q.type)
    && (q.type !== "single_select" || q.options.length > 0 && q.options.length <= 25 && q.options.every(o => o.length > 0 && o.length <= 100)));
}
interface SignupAccount { tag: string; name: string; townhall: number; isVerified: boolean; signedUp: boolean }
async function joinModal(ctx: CommandContext, id: string, page?: number, removing = false) {
  // Modal responses cannot be deferred: cap this one read below Discord's acknowledgement deadline.
  const [roster, result, emojis] = await Promise.all([load(ctx, id, true), ctx.services.api.get<{ items: SignupAccount[]; remainingSlots?: number | null }>(
    endpoint(ctx, id) + "/accounts", { discordUserId: invokingUserId(ctx) }, AbortSignal.timeout(1500)),
    ctx.services.discordRest.listApplicationEmojis(AbortSignal.timeout(1500))]);
  const accounts = result.items.filter(a => removing ? a.signedUp : !a.signedUp && (!roster.requireVerified || a.isVerified));
  if (!accounts.length) return reply(t(ctx, "roster.empty"));
  const action = removing ? "leave" : "join";
  if (accounts.length > 25 && page === undefined) {
    // A page selector avoids silently hiding accounts beyond Discord's option limit.
    return legacyMessage({ components: [actionRow({ type: 3, custom_id: `ck:roster:${action}-page:${id}`,
      options: Array.from({ length: Math.ceil(accounts.length / 25) }, (_, i) => ({
        label: `${i * 25 + 1}–${Math.min((i + 1) * 25, accounts.length)}`, value: String(i),
      })).slice(0, 25) })] }, { ephemeral: true });
  }
  const selected = accounts.slice((page ?? 0) * 25, ((page ?? 0) + 1) * 25);
  if (!selected.length) return reply(t(ctx, "error.invalidInteraction"));
  const questions = removing ? [] : questionsFor(roster);
  if (!supported(questions)) return reply(t(ctx, "roster.formUnsupported"));
  const maxAccounts = removing || questions.length > 0 ? 1 : Math.min(selected.length, result.remainingSlots ?? selected.length);
  if (maxAccounts < 1) return reply(t(ctx, "roster.empty"));
  return { type: 9, data: { custom_id: removing ? `ck:roster:withdraw:${id}` : `ck:roster:submit:${id}:${await formVersion(questions)}`, title: t(ctx, removing ? "roster.leave" : "roster.join"), components: [
    { type: 18, label: t(ctx, "roster.accounts"), component: { type: 3, custom_id: "player", min_values: 1, max_values: maxAccounts,
      options: selected.map(a => {
        const emoji = emojis.find(e => e.name === `th${a.townhall}`);
        return { label: `${a.name} (${a.tag})`.slice(0, 100), value: a.tag,
          ...(emoji ? { emoji: { id: emoji.id, name: emoji.name, animated: emoji.animated ?? false } } : {}) };
      }) } },
    ...questions.map((q, i) => q.type === "text" ? { type: 18, label: q.label, component: {
      type: 4, custom_id: `q${i}`, style: 2, required: q.required, max_length: 1000,
    } } : { type: 18, label: q.label, component: { type: 3, custom_id: `q${i}`, required: q.required,
      min_values: q.required ? 1 : 0, max_values: 1, options: q.type === "boolean"
        ? [{ label: t(ctx, "roster.yes"), value: "true" }, { label: t(ctx, "roster.no"), value: "false" }]
        : q.options.map((label, index) => ({ label, value: String(index) })),
    } }),
  ] } };
}
async function submit(ctx: CommandContext, id: string, version: string) {
  const roster = await load(ctx, id);
  const questions = questionsFor(roster);
  if (!supported(questions) || await formVersion(questions) !== version) return reply(t(ctx, "roster.formUnsupported"));
  const fields = modalFields(ctx.interaction.data?.components);
  const selections = fields.get("player")?.values;
  if (selections && selections.length > 1) {
    if (questions.length > 0 || selections.length > 25) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
    const playerTags = selections.map(value => normalizeTag(value, ctx.locale));
    if (new Set(playerTags).size !== playerTags.length) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
    await ctx.services.api.post(endpoint(ctx, id) + "/submissions/batch", { playerTags, discordUserId: invokingUserId(ctx) });
    return reply(t(ctx, "roster.saved"));
  }
  const player = fields.get("player")?.values?.[0] ?? fields.get("player")?.value ?? "";
  if (player.length > 12) throw new CommandInputError(t(ctx, "error.tag"));
  const tag = normalizeTag(player, ctx.locale);
  const links = await ctx.services.api.get<{ items: Array<{ player_tag: string; is_verified: boolean }> }>(`/v2/links/${invokingUserId(ctx)}`);
  if (!links.items.some(l => l.player_tag === tag && (!roster.requireVerified || l.is_verified))) return reply(t(ctx, "roster.linkRequired"));
  const answers: Record<string, string | boolean> = {};
  for (const [i, q] of questions.entries()) {
    const field = fields.get(`q${i}`);
    const raw = q.type === "text" ? field?.value : field?.values?.[0];
    if (raw === undefined || raw.trim() === "") {
      if (q.required) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
      continue;
    }
    if (q.type === "text") {
      if (raw.length > 1000) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
      answers[q.id] = raw;
    } else if (q.type === "boolean" && ["true", "false"].includes(raw)) answers[q.id] = raw === "true";
    else if (q.type === "single_select" && /^(0|[1-9]\d*)$/.test(raw) && q.options[Number(raw)] !== undefined) answers[q.id] = q.options[Number(raw)]!;
    else throw new CommandInputError(t(ctx, "error.invalidInteraction"));
  }
  // The API rechecks ownership under a lock. Never omit the signed actor's ID.
  await ctx.services.api.post(endpoint(ctx, id) + "/submissions", { playerTag: tag, answers, discordUserId: invokingUserId(ctx) });
  return reply(t(ctx, "roster.saved"));
}
async function post(ctx: CommandContext, id: string, mode = "signup") {
  requireManager(ctx);
  const channelId = ctx.interaction.channel_id;
  if (!channelId) throw new CommandInputError(t(ctx, "base.missingChannel"));
  const shared = { ...ctx, locale: resolveLocale(ctx.interaction.guild_locale) };
  await ctx.services.api.post(endpoint(ctx, id) + "/post", {
    channelId, mode, nonce: ctx.interaction.id, dashboardUrl: rosterDashboardUrl(ctx, id),
    joinLabel: t(shared, "roster.join"), leaveLabel: t(shared, "roster.leave"), viewLabel: t(shared, "roster.view"),
  });
  return reply(t(ctx, "roster.posted"));
}

/** Strict routing keeps modal submissions separate from public buttons, with no in-memory sessions. */
export async function dispatchRoster(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void): Promise<DiscordInteractionResponse> {
  const parts = (ctx.interaction.data?.custom_id ?? "").split(":");
  if (parts[2] === "ping-send") return guarded(ctx, async () => {
    requireManager(ctx);
    if (ctx.interaction.type !== InteractionType.MessageComponent) return reply(t(ctx, "error.invalidInteraction"));
    const run = () => confirmRosterPing(ctx, parts);
    if (!waitUntil) return run();
    waitUntil(guarded(ctx, run).then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {})));
    return { type: 5, data: { flags: 64 } };
  });
  const [, , action, id, extra] = parts;
  const modal = ctx.interaction.type === InteractionType.ModalSubmit;
  const valid = parts.length <= 5 && ((action === "create" || action === "select") && parts.length === 3
    || action === "list" && parts.length === 4 && /^\d{1,6}$/.test(id ?? "")
    || ["view", "join", "leave", "join-page", "leave-page", "withdraw", "post", "submit", "refresh"].includes(action ?? "") && uuid.test(id ?? "")
      && (action === "submit" ? parts.length === 5 && /^[a-f0-9]{16}$/.test(extra ?? "")
        : action === "view" ? parts.length === 4 || parts.length === 5 && /^\d{1,6}$/.test(extra ?? "") : parts.length === 4));
  if (!valid || modal !== ["submit", "withdraw"].includes(action ?? "")) return reply(t(ctx, "error.invalidInteraction"));
  const run = () => guarded(ctx, async () => {
    switch (action) {
      case "create": return createModal(ctx);
      case "list": return list(ctx, Number(id));
      case "select": {
        const selected = ctx.interaction.data?.values;
        if (selected?.length !== 1 || !uuid.test(selected[0]!)) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
        return view(ctx, selected[0]!);
      }
      case "view": return view(ctx, id!, Number(extra ?? 0));
      case "join": return joinModal(ctx, id!);
      case "leave": return joinModal(ctx, id!, undefined, true);
      case "join-page":
      case "leave-page": {
        const value = ctx.interaction.data?.values?.[0];
        if (!/^\d{1,6}$/.test(value ?? "")) return reply(t(ctx, "error.invalidInteraction"));
        return joinModal(ctx, id!, Number(value), action === "leave-page");
      }
      case "withdraw": {
        const tag = normalizeTag(modalFields(ctx.interaction.data?.components).get("player")?.values?.[0] ?? "", ctx.locale);
        await ctx.services.api.post(endpoint(ctx, id!) + "/withdraw", { playerTag: tag, discordUserId: invokingUserId(ctx) });
        return reply(t(ctx, "roster.saved"));
      }
      case "submit": return submit(ctx, id!, extra!);
      case "post": return post(ctx, id!);
      case "refresh": {
        requireManager(ctx);
        await ctx.services.api.post(endpoint(ctx, id!) + "/refresh-publication", {});
        return { type: InteractionResponseType.DeferredUpdateMessage };
      }
      default: return reply(t(ctx, "error.invalidInteraction"));
    }
  });
  if (action === "refresh" && waitUntil) {
    waitUntil(run().then(response => response.type === InteractionResponseType.DeferredUpdateMessage
      ? undefined : ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token, response.data ?? {})));
    return { type: InteractionResponseType.DeferredUpdateMessage };
  }
  if (!waitUntil || ["create", "join", "leave", "join-page", "leave-page"].includes(action ?? "")) return run();
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {})));
  return { type: InteractionResponseType.DeferredChannelMessageWithSource, data: { flags: 64 } };
}
