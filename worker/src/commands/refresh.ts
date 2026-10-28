import { localizations } from "../localization/catalog";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, InteractionType, MessageFlags } from "../discord/types";
import { drainRefreshJobs } from "../refresh/runtime";
import { refreshCategories, type RefreshCategory } from "../refresh/plan";
import { CommandInputError, invokingUserId, OptionType, requireGuildId, stringOption } from "./command-utils";
import type { Command, CommandContext } from "./types";

const labels: Record<RefreshCategory, string> = { roster: "Roster membership", tenure: "Discord tenure", family: "Family membership", clan: "Clan membership", leadership: "Clan leadership",
  townhall: "Town Hall", builderhall: "Builder Hall", league: "Home Village league", builder_league: "Builder Base league", category: "Clan category", nicknames: "Nickname" };
type RoleTreatment = "add" | "remove" | "both";
const roleTreatment = (value: string | undefined): RoleTreatment => {
  if (value === undefined) return "both";
  if (value !== "add" && value !== "remove" && value !== "both") throw new CommandInputError("Choose Add only, Remove only, or Both");
  return value;
};
const bool = (ctx: CommandContext, name: string) => ctx.options.get(name)?.value === true;
export const refreshCommand: Command = {
  deferred: true, ephemeral: true,
  definition: { name_localizations: localizations("refresh.name"), description_localizations: localizations("refresh.description"), name: "refresh", description: "Refresh your roles and nickname, or refresh a member or role", type: 1, contexts: [0], integration_types: [0],
    options: [
      { name: "role_or_user", description: "Member or role to refresh (defaults to yourself)", type: OptionType.Mentionable },
      { name: "test", description: "Preview the changes without applying them", type: OptionType.Boolean },
      { name: "role_treatment", description: "Only add roles, only remove roles, or both (nickname is independent)", type: OptionType.String,
        choices: [{ name: "Both", value: "both" }, { name: "Add only", value: "add" }, { name: "Remove only", value: "remove" }] },
      { name: "advanced_mode", description: "Choose which role categories and nickname to refresh", type: OptionType.Boolean },
    ] },
  async execute(ctx) {
    requireGuildId(ctx);
    const treatment = roleTreatment(stringOption(ctx, "role_treatment"));
    const target = stringOption(ctx, "role_or_user") ?? invokingUserId(ctx);
    const kind = ctx.interaction.data?.resolved?.roles?.[target] ? "role" : "user";
    if (bool(ctx, "advanced_mode")) return legacyMessage({ content: "Choose what to refresh. Other categories stay as they are.", components: [actionRow({
      type: 3, custom_id: `ck:refresh:choose:${invokingUserId(ctx)}:${kind}:${target}:${bool(ctx, "test") ? "1" : "0"}:${treatment}`,
      min_values: 1, max_values: refreshCategories.length,
      options: refreshCategories.map(value => ({ label: labels[value], value })),
    })] }, { ephemeral: true });
    return enqueue(ctx, kind, target, bool(ctx, "test"), [...refreshCategories], treatment);
  },
};

async function enqueue(ctx: CommandContext, kind: string, target: string, preview: boolean, categories: RefreshCategory[], treatment: RoleTreatment = "both") {
  const guild = requireGuildId(ctx), actor = invokingUserId(ctx);
  if (treatment !== "both") {
    // An older API ignores unknown body fields and would queue an unrestricted
    // job. Check support before creating it, not after Discord work can begin.
    let supported = false;
    try { supported = (await ctx.services.api.get<{ roleTreatment?: boolean }>("/v2/bot/role-refresh/capabilities")).roleTreatment === true; } catch { /* unavailable support must not enqueue a broader job */ }
    if (!supported) throw new CommandInputError("This refresh option is not available yet. Try Both or ask a server admin for help.");
  }
  const result = await ctx.services.api.post<{ requestId: string; queued: number }>(`/v2/bot/role-refresh/${guild}/enqueue`, {
    actorId: actor, requestId: ctx.interaction.id, targetId: target, targetKind: kind, preview, categories, roleTreatment: treatment,
  });
  // Durable insertion happens before any Discord work. An interrupted command
  // retains its jobs; the scheduled consumer picks them up on the next minute.
  await drainRefreshJobs(ctx.services, result.requestId, guild);
  return status(ctx, result.requestId);
}

async function status(ctx: CommandContext, requestId: string) {
  const guild = requireGuildId(ctx);
  const result = await ctx.services.api.get<{ total: number; completed: number; failed: number; results: Array<{ user_id: string; result: { add?: string[]; remove?: string[]; nickname?: string; blocked?: string[]; preview?: boolean; skipped?: string; error?: string } }> }>(`/v2/bot/role-refresh/${guild}/status`, {
    requestId, actorId: invokingUserId(ctx),
  });
  const detail = result.results.map(item => {
    const value = item.result;
    return `<@${item.user_id}>: ${value.skipped ?? value.error ?? `${value.preview ? "Would add" : "Added"} ${value.add?.length ?? 0}, ${value.preview ? "remove" : "removed"} ${value.remove?.length ?? 0}${value.nickname ? `; nickname: ${value.nickname}` : ""}${value.blocked?.length ? `; ${value.blocked.length} blocked change(s)` : ""}`}`;
  }).join("\n");
  return legacyMessage({ content: `${result.completed}/${result.total} refreshes completed${result.failed ? `; ${result.failed} failed` : ""}.${result.completed < result.total ? " Remaining refreshes are queued." : ""}\n${detail}`.slice(0, 1950),
    allowed_mentions: { parse: [] }, components: [actionRow({ type: 2, style: 2, label: "Refresh status", custom_id: `ck:refresh:status:${invokingUserId(ctx)}:${requestId}` })] }, { ephemeral: true });
}

export async function dispatchRefresh(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  if (ctx.interaction.type !== InteractionType.MessageComponent) throw new CommandInputError("Invalid refresh action");
  const [, , action, actor, first, second, preview, treatment] = (ctx.interaction.data?.custom_id ?? "").split(":");
  if (actor !== invokingUserId(ctx)) throw new CommandInputError("This refresh menu belongs to another person");
  const run = async () => {
    if (action === "status" && first && /^\d{15,20}$/u.test(first)) return status(ctx, first);
    const values = ctx.interaction.data?.values ?? [];
    if (action !== "choose" || !["user", "role"].includes(first ?? "") || !/^\d{15,20}$/u.test(second ?? "")
      || !["0", "1"].includes(preview ?? "") || !values.length || values.some(value => !refreshCategories.includes(value as RefreshCategory))) {
      throw new CommandInputError("Invalid refresh selection");
    }
    return enqueue(ctx, first!, second!, preview === "1", values as RefreshCategory[], roleTreatment(treatment));
  };
  if (!waitUntil) return run();
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {}),
    error => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, { content: error instanceof CommandInputError ? error.message : "Refresh could not finish. Please try again.", flags: MessageFlags.Ephemeral })));
  return { type: InteractionResponseType.DeferredChannelMessageWithSource, data: { flags: MessageFlags.Ephemeral } };
}

export const mainAccountCommand: Command = {
  deferred: true, ephemeral: true,
  definition: { name_localizations: localizations("mainAccount.name"), description_localizations: localizations("mainAccount.description"), name: "main-account", description: "Choose your main Clash account for this server's nickname", type: 1, contexts: [0], integration_types: [0],
    options: [{ name: "player", description: "One of your visible linked accounts", type: OptionType.String, required: true, autocomplete: true }] },
  async autocomplete(ctx) {
    const items = await ctx.services.api.get<{ items: Array<{ player_tag: string; hidden: boolean }> }>(`/v2/links/${invokingUserId(ctx)}`);
    const query = stringOption(ctx, "player")?.toUpperCase() ?? "";
    return items.items.filter(item => !item.hidden && item.player_tag.includes(query)).slice(0, 25).map(item => ({ name: item.player_tag, value: item.player_tag }));
  },
  async execute(ctx) {
    const guild = requireGuildId(ctx), actor = invokingUserId(ctx);
    const tag = stringOption(ctx, "player");
    if (!tag) throw new CommandInputError("Choose a visible linked account");
    const result = await ctx.services.api.post<{ tag: string }>(`/v2/bot/role-refresh/${guild}/main`, { actorId: actor, tag });
    const response = await enqueue(ctx, "user", actor, false, ["nicknames"]);
    return { ...response, data: { ...response.data, content: `Main account for this server: ${result.tag}.\n${response.data?.content ?? ""}` } };
  },
};
