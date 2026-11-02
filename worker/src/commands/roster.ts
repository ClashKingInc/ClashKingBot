import { interactionErrorReply } from "./errors";
import { ApplicationEmojis } from "../discord/emojis";
import { actionRow, legacyMessage, type ButtonComponent } from "../discord/components";
import { InteractionResponseType, InteractionType, type DiscordInteractionResponse } from "../discord/types";
import { localizations, translate } from "../localization/catalog";
import { CommandInputError, invokingUserId, normalizeTag, requireGuildId } from "./command-utils";
import { emojis, playerAutocomplete, escapeMarkdown } from "./game-common";
import { modalFields } from "./modals";
import type { Command, CommandContext } from "./types";

// Projections of api-contracts/src/bot-server.ts; never Dashboard's snake_case response.
interface Question { id: string; label: string; type: string; required: boolean; options: string[]; order: number }
export interface Roster {
  id: string; serverId: string; alias: string; description: string | null; memberCount: number;
  clanTag?: string | null;
  requireVerified?: boolean;
  questionnaire: { questions: Question[] };
  members: Array<{ playerTag: string; playerName: string; townhall: number; clanName: string | null; memberGroupId?: string | null; memberGroupName?: string | null }>;
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
export const rosterCommand: Command = {
  deferred: true, ephemeral: true,
  definition: { name: "roster", type: 1, contexts: [0], integration_types: [0], description: translate("roster.title"),
    description_localizations: localizations("roster.title"), options: [
      { name: "post", type: 1, description: "Post a saved roster to this channel", options: [rosterOption, { name:"type",type:3,required:true,description:"Publication type",choices:[{name:"Signup",value:"signup"},{name:"Post",value:"post"},{name:"Static",value:"static"}]}] },
      { name: "search", type: 1, description: "Find this server's rosters for a player or Discord user", options: [
        { name: "player", type: 3, description: "Player tag to find", autocomplete: true },
        { name: "user", type: 6, description: "Linked Discord user (default you)" },
      ] },
    ] },
  autocomplete: async (ctx) => {
    requireGuildId(ctx);
    const options = ctx.interaction.data?.options?.[0]?.options ?? [];
    const focused = options.find(option => option.focused);
    if (focused?.name === "player") return playerAutocomplete({...ctx,options:new Map(options.map(option=>[option.name,option]))});
    if (focused?.name !== "roster") return [];
    const query = String(focused?.value ?? "").toLocaleLowerCase();
    const { items } = await ctx.services.api.get<{ items: Roster[] }>(endpoint(ctx), {}, AbortSignal.timeout(1500));
    return items.filter(r => r.serverId === requireGuildId(ctx) && uuid.test(r.id) && `${r.alias} ${r.clanTag ?? ""}`.toLocaleLowerCase().includes(query))
      .sort((a, b) => a.alias.localeCompare(b.alias)).slice(0, 25)
      .map(r => ({ name: `${r.alias} | ${r.clanTag ?? "—"} | 👥 ${r.memberCount}`.slice(0, 100), value: r.id }));
  },
  execute: (ctx) => guarded(ctx, async () => {
    const sub = ctx.interaction.data?.options?.[0];
    // Cached slash definitions must not revive dashboard-only roster mutations.
    if (!sub || !["post", "search"].includes(sub.name))
      throw new CommandInputError("Manage rosters in the dashboard.");
    const options = new Map(sub?.options?.map(option => [option.name, option.value]));
    if (sub?.name === "search") {
      if (options.has("player") && options.has("user")) throw new CommandInputError("Choose either a player or a Discord user.");
      return searchRosters(ctx,options.has("player")?`p~${normalizeTag(String(options.get("player")),ctx.locale)}`:`u~${String(options.get("user")??invokingUserId(ctx))}`);
    }
    const id = String(options.get("roster") ?? "");
    if (!uuid.test(id)) throw new CommandInputError(t(ctx, "error.invalidInteraction"));
    if (sub?.name === "post") {
      requireManager(ctx);
      const channelId=ctx.interaction.channel_id, mode=String(options.get("type")??"");
      if(!channelId || !["signup","post","static"].includes(mode))throw new CommandInputError("Choose a publication type and a server text channel.");
      const dashboard=new URL("/dashboard/rosters/detail",ctx.env.DASHBOARD_BASE_URL);
      dashboard.searchParams.set("guildId",requireGuildId(ctx));dashboard.searchParams.set("rosterId",id);
      // Use the dashboard's publisher, including its saved layout and signup
      // controls. The interaction ID makes retries of this submission stable.
      const result=await ctx.services.api.post<{messageId:string}>(endpoint(ctx,id)+"/post",{
        channelId,mode,nonce:ctx.interaction.id,dashboardUrl:dashboard.toString(),
        joinLabel:"Sign up",leaveLabel:"Remove signup",viewLabel:"Dashboard",
      });
      return reply(`[Roster posted](https://discord.com/channels/${requireGuildId(ctx)}/${channelId}/${result.messageId}).`);
    }
    throw new CommandInputError(t(ctx, "error.invalidInteraction"));
  }),
};

async function guarded(ctx: CommandContext, run: () => Promise<DiscordInteractionResponse>) {
  try { requireGuildId(ctx); return await run(); }
  catch (error) {
    return interactionErrorReply(error,ctx.interaction);
  }
}
async function searchRosters(ctx:CommandContext,target:string,requestedPage=0):Promise<DiscordInteractionResponse>{
  if(!/^(?:p~#[0289PYLQGRJCUV]{1,15}|u~[0-9]{15,20})$/u.test(target))throw new CommandInputError("Choose a valid player or Discord user.");
  const serverId=requireGuildId(ctx);
  const tags=target.startsWith("p~")?[target.slice(2)]:(await ctx.services.api.get<{items:Array<{player_tag:string;hidden?:boolean}>}>(`/v2/links/${target.slice(2)}`)).items.filter(row=>!row.hidden).map(row=>row.player_tag);
  const wanted=new Set(tags);
  const {items}=await ctx.services.api.get<{items:Roster[]}>(endpoint(ctx));
  const rosters=items.filter(row=>row.serverId===serverId&&uuid.test(row.id));
  if(rosters.length>100)throw new CommandInputError("This search supports up to 100 server rosters.");
  const names=new Map(rosters.map(row=>[row.id,row.alias]));
  const found:Array<{rosterId:string;playerTag:string;playerName?:string;townhall?:number;clanName?:string|null;memberGroupName?:string|null}>=[];
  // Query only display fields, never signup answers or private activity. Scope
  // every batch to the invoking server; self-search must not leak other servers.
  if(wanted.size)for(let offset=0;offset<rosters.length;offset+=25){
    const result=await ctx.services.api.post<{rows:typeof found}>("/v2/roster/members/query",{serverId,rosterIds:rosters.slice(offset,offset+25).map(row=>row.id),fields:["playerName","townhall","clanName"]});
    found.push(...result.rows.filter(row=>wanted.has(row.playerTag)&&names.has(row.rosterId)));
  }
  for(const id of new Set(found.map(row=>row.rosterId))){
    const roster=await load(ctx,id);
    for(const row of found.filter(row=>row.rosterId===id))row.memberGroupName=roster.members.find(member=>member.playerTag===row.playerTag)?.memberGroupName;
  }
  found.sort((a,b)=>(a.playerName??a.playerTag).localeCompare(b.playerName??b.playerTag)||(names.get(a.rosterId)??"").localeCompare(names.get(b.rosterId)??""));
  const emoji=await emojis(ctx), blocks:string[]=[];
  for(const tag of wanted){
    const matches=found.filter(row=>row.playerTag===tag);if(!matches.length)continue;
    const first=matches[0]!;
    blocks.push(`${emoji.get(first.townhall??0)} **${escapeMarkdown(first.playerName??tag)}**\n`+matches.map(row=>`${escapeMarkdown(names.get(row.rosterId)??"Roster")} | ${escapeMarkdown(row.clanName??"No clan")} | ${escapeMarkdown(row.memberGroupName??"Main")}`).join("\n"));
  }
  const pages:string[]=[];let description="";
  for(const block of blocks){if(description.length+block.length+2>3700&&description){pages.push(description);description="";}description+=(description?"\n\n":"")+block;}
  if(description)pages.push(description);
  if(!pages.length)pages.push("Not found on any rosters in this server.");
  const page=Math.min(Math.max(0,requestedPage),pages.length-1);
  const person=target.startsWith("p~")?found[0]?.playerName??target.slice(2):target.slice(2)===invokingUserId(ctx)?ctx.interaction.member?.nick??ctx.interaction.member?.user?.global_name??ctx.interaction.member?.user?.username:"this user";
  const embeds=[{author:{name:`Rosters for ${person}`},color:0x2ecc71,description:pages[page]!,...(pages.length>1?{footer:{text:`Page ${page+1} of ${pages.length}`}}:{})}];
  const id=(p:number)=>`ck:roster:search:${target}:${p}`;
  return legacyMessage({allowed_mentions:{parse:[]},embeds,components:[actionRow(
    ...(page?[{type:2 as const,style:2 as const,label:"Previous",custom_id:id(page-1)}]:[]),
    {type:2,style:2,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id(page)},
    ...(page+1<pages.length?[{type:2 as const,style:2 as const,label:"Next",custom_id:id(page+1)}]:[]),
  )]},{ephemeral:true});
}
function rosterText(ctx: CommandContext, roster: Roster, page: number): string {
  const members = roster.members.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const digits = "⁰¹²³⁴⁵⁶⁷⁸⁹";
  const lines = members.map(m => `${String(m.townhall).replace(/\d/g, n => digits[Number(n)] ?? n)}${clean(m.playerName, 30)} (${clean(m.playerTag, 15)}) | ${clean(m.clanName ?? "—", 25)}${m.memberGroupName ? ` · ${clean(m.memberGroupName,49)}` : ""}`);
  return `**${clean(roster.alias, 100)}** · 👥 ${roster.members.length}\n${clean(roster.description ?? "", 300)}\n\n${lines.join("\n") || t(ctx, "roster.empty")}\n\n${page + 1}/${Math.max(1, Math.ceil(roster.members.length / PAGE_SIZE))}`;
}
async function view(ctx: CommandContext, id: string, page = 0) {
  const roster = await load(ctx, id);
  const last = Math.max(0, Math.ceil(roster.members.length / PAGE_SIZE) - 1);
  page = Math.min(page, last);
  const refresh = (await emojis(ctx)).component("refresh") ?? { name: "↻" };
  const controls: ButtonComponent[] = [button(ctx, "join", "roster.join", id),{type:2,style:2,emoji:refresh,custom_id:`ck:roster:view:${id}:${page}`}];
  if (page > 0) controls.push({ type: 2, style: 2, label: "←", custom_id: `ck:roster:view:${id}:${page - 1}` });
  if (page < last) controls.push({ type: 2, style: 2, label: "→", custom_id: `ck:roster:view:${id}:${page + 1}` });
  return { type: 4, data: { content: rosterText(ctx, roster, page), flags: 64, allowed_mentions: { parse: [] }, components: [actionRow(...controls)] } };
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
  if (!accounts.length) return interactionErrorReply(new CommandInputError(t(ctx,"roster.empty")),ctx.interaction);
  const action = removing ? "leave" : "join";
  if (accounts.length > 25 && page === undefined) {
    // A page selector avoids silently hiding accounts beyond Discord's option limit.
    return legacyMessage({ components: [actionRow({ type: 3, custom_id: `ck:roster:${action}-page:${id}`,
      options: Array.from({ length: Math.ceil(accounts.length / 25) }, (_, i) => ({
        label: `${i * 25 + 1}–${Math.min((i + 1) * 25, accounts.length)}`, value: String(i),
      })).slice(0, 25) })] }, { ephemeral: true });
  }
  const selected = accounts.slice((page ?? 0) * 25, ((page ?? 0) + 1) * 25);
  if (!selected.length) return interactionErrorReply(new CommandInputError(t(ctx,"error.invalidInteraction")),ctx.interaction);
  const questions = removing ? [] : questionsFor(roster);
  if (!supported(questions)) return interactionErrorReply(new CommandInputError(t(ctx,"roster.formUnsupported")),ctx.interaction);
  const maxAccounts = removing || questions.length > 0 ? 1 : Math.min(selected.length, result.remainingSlots ?? selected.length);
  if (maxAccounts < 1) return interactionErrorReply(new CommandInputError(t(ctx,"roster.empty")),ctx.interaction);
  return { type: 9, data: { custom_id: removing ? `ck:roster:withdraw:${id}` : `ck:roster:submit:${id}:${await formVersion(questions)}`, title: t(ctx, removing ? "roster.leave" : "roster.join"), components: [
    { type: 18, label: t(ctx, "roster.accounts"), component: { type: 3, custom_id: "player", min_values: 1, max_values: maxAccounts,
      options: selected.map(a => {
        const emoji = new ApplicationEmojis(emojis).component(a.townhall);
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
  if (!supported(questions) || await formVersion(questions) !== version) return interactionErrorReply(new CommandInputError(t(ctx,"roster.formUnsupported")),ctx.interaction);
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
/** Keep existing member signup and display refresh controls working. Setup and
 * staff roster edits are dashboard-only, including stale buttons after removal. */
export async function dispatchRoster(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void): Promise<DiscordInteractionResponse> {
  const parts = (ctx.interaction.data?.custom_id ?? "").split(":");
  const [, , action, id, extra] = parts;
  const modal = ctx.interaction.type === InteractionType.ModalSubmit;
  const valid = parts.length <= 5 && (action === "search" && (parts.length === 4 || parts.length === 5 && /^\d{1,6}$/.test(extra??"")) && /^(?:p~#[0289PYLQGRJCUV]{1,15}|u~[0-9]{15,20})$/u.test(id ?? "")
    || ["view", "join", "leave", "join-page", "leave-page", "withdraw", "submit", "refresh"].includes(action ?? "") && uuid.test(id ?? "")
      && (action === "submit" ? parts.length === 5 && /^[a-f0-9]{16}$/.test(extra ?? "")
        : action === "view" ? parts.length === 4 || parts.length === 5 && /^\d{1,6}$/.test(extra ?? "") : parts.length === 4));
  if (!valid || modal !== ["submit", "withdraw"].includes(action ?? "")) return interactionErrorReply(new CommandInputError(t(ctx,"error.invalidInteraction")),ctx.interaction);
  const run = () => guarded(ctx, async () => {
    switch (action) {
      case "search": return searchRosters(ctx,id!,Number(extra??0));
      case "view": return view(ctx, id!, Number(extra ?? 0));
      case "join": return joinModal(ctx, id!);
      case "leave": return joinModal(ctx, id!, undefined, true);
      case "join-page":
      case "leave-page": {
        const value = ctx.interaction.data?.values?.[0];
        if (!/^\d{1,6}$/.test(value ?? "")) return interactionErrorReply(new CommandInputError(t(ctx,"error.invalidInteraction")),ctx.interaction);
        return joinModal(ctx, id!, Number(value), action === "leave-page");
      }
      case "withdraw": {
        const tag = normalizeTag(modalFields(ctx.interaction.data?.components).get("player")?.values?.[0] ?? "", ctx.locale);
        await ctx.services.api.post(endpoint(ctx, id!) + "/withdraw", { playerTag: tag, discordUserId: invokingUserId(ctx) });
        return reply(t(ctx, "roster.saved"));
      }
      case "submit": return submit(ctx, id!, extra!);
      case "refresh": {
        requireManager(ctx);
        await ctx.services.api.post(endpoint(ctx, id!) + "/refresh-publication", {});
        return { type: InteractionResponseType.DeferredUpdateMessage };
      }
      default: return interactionErrorReply(new CommandInputError(t(ctx,"error.invalidInteraction")),ctx.interaction);
    }
  });
  if (action === "refresh" && waitUntil) {
    waitUntil(run().then(response => response.type === InteractionResponseType.DeferredUpdateMessage
      ? undefined : ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token, response.data ?? {})));
    return { type: InteractionResponseType.DeferredUpdateMessage };
  }
  if (!waitUntil || ["join", "leave", "join-page", "leave-page"].includes(action ?? "")) return run();
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {})));
  return { type: InteractionResponseType.DeferredChannelMessageWithSource, data: { flags: 64 } };
}
