import { legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, requireGuildId, stringOption } from "./command-utils";
import { subcommand } from "./game-common";
import type { Command } from "./types";

interface Settings {
  auto_eval_triggers?: string[] | null;
  auto_eval_status?: boolean; auto_eval_nickname?: boolean;
  auto_eval_role_treatment?: "add" | "remove" | "both"; auto_eval_blacklist_roles?: string[];
}
const triggerNames = { member_join: "Member join", member_leave: "Member leave", townhall_change: "Town Hall change", league_change: "League change", role_change: "Clan role change" };
export const autoRefreshCommand: Command = {
  deferred: true, ephemeral: true,
  definition: { name: "autorefresh", description: "Configure automatic game-role refresh", type: 1, contexts: [0], integration_types: [0], default_member_permissions: "32",
    options: [{ name: "options", description: "View or update automatic refresh settings", type: OptionType.Subcommand, options: [
      { name: "state", description: "Enable automatic game-role refresh", type: OptionType.Boolean },
      { name: "role_treatment", description: "Add roles, remove roles, or both", type: OptionType.String,
        choices: [{ name: "Both", value: "both" }, { name: "Add only", value: "add" }, { name: "Remove only", value: "remove" }] },
      { name: "nickname_change", description: "Allow automatic nickname changes", type: OptionType.Boolean },
      { name: "blacklist_role_add", description: "Skip game-triggered refresh for members with this role", type: OptionType.Role },
      { name: "blacklist_role_remove", description: "Remove this role from automatic refresh exclusions", type: OptionType.Role },
    ] }, { name: "triggers", description: "View or select the game events that refresh roles", type: OptionType.Subcommand, options: [
      { name: "mode", description: "Choose all profile changes, selected events, or no game events", type: OptionType.String,
        choices: [{ name: "All profile changes (default)", value: "all" }, { name: "Selected events", value: "selected" }, { name: "No game events", value: "none" }] },
      ...Object.entries(triggerNames).map(([name, label]) => ({ name, description: `${label} triggers a refresh`, type: OptionType.Boolean })),
    ] }] },
  async execute(context) {
    const ctx = subcommand(context), server = requireGuildId(ctx), permission = ctx.interaction.member?.permissions ?? "0";
    if (!/^\d+$/u.test(permission) || (BigInt(permission) & 40n) === 0n) throw new CommandInputError("Manage Server is required.");
    const path = `/v2/server/${server}/role-settings`;
    let settings = await ctx.services.api.get<Settings>(path);
    if (ctx.path[0] === "triggers") {
      if (settings.auto_eval_triggers === undefined) throw new CommandInputError("Trigger selection is not available yet.");
      const mode = stringOption(ctx, "mode"), changes = Object.keys(triggerNames).filter(key => ctx.options.has(key));
      if (mode && !["all", "selected", "none"].includes(mode)) throw new CommandInputError("Choose a valid trigger mode.");
      if (changes.length && (mode === "all" || mode === "none")) throw new CommandInputError("Use Selected events when choosing individual triggers.");
      if (mode || changes.length) {
        let selected: string[] | null = mode === "all" ? null : mode === "none" ? [] : [...(settings.auto_eval_triggers ?? Object.keys(triggerNames))];
        for (const key of changes) {
          const enabled = ctx.options.get(key)?.value;
          if (typeof enabled !== "boolean") throw new CommandInputError("Choose On or Off for each trigger.");
          selected = selected!.filter(value => value !== key);
          if (enabled) selected.push(key);
        }
        await ctx.services.api.patch(path, { auto_eval_triggers: selected });
        settings = await ctx.services.api.get<Settings>(path);
      }
      const selected = settings.auto_eval_triggers;
      return legacyMessage({ allowed_mentions: { parse: [] }, content: `Automatic game events: **${selected === null ? "All profile changes (default)" : selected?.length ? selected.map(value => triggerNames[value as keyof typeof triggerNames]).join(", ") : "None"}**\nManual refreshes, settings changes, account linking, roster and tenure processing remain independent.` }, { ephemeral: true });
    }
    const treatment = stringOption(ctx, "role_treatment"), add = stringOption(ctx, "blacklist_role_add"), remove = stringOption(ctx, "blacklist_role_remove");
    if (add && add === remove) throw new CommandInputError("Choose different roles to add and remove.");
    if ([add, remove].some(id => id && (!/^\d{15,20}$/u.test(id) || id === server))) throw new CommandInputError("Choose a valid role other than @everyone.");
    if (treatment && !["add", "remove", "both"].includes(treatment)) throw new CommandInputError("Choose Add only, Remove only, or Both.");
    if ((treatment || add || remove) && (settings.auto_eval_role_treatment === undefined || !Array.isArray(settings.auto_eval_blacklist_roles))) {
      throw new CommandInputError("These automatic refresh options are not available yet.");
    }
    const patch: Record<string, unknown> = {};
    for (const [option, field] of [["state", "auto_eval_status"], ["nickname_change", "auto_eval_nickname"]] as const) {
      const value = ctx.options.get(option)?.value;
      if (value !== undefined) {
        if (typeof value !== "boolean") throw new CommandInputError("Choose On or Off.");
        patch[field] = value;
      }
    }
    if (treatment) patch.auto_eval_role_treatment = treatment;
    if (add || remove) patch.auto_eval_blacklist_roles = [...new Set([...(settings.auto_eval_blacklist_roles ?? []), ...(add ? [add] : [])])].filter(id => id !== remove).sort();
    if (Object.keys(patch).length) {
      await ctx.services.api.patch(path, patch);
      settings = await ctx.services.api.get<Settings>(path);
    }
    const roles = settings.auto_eval_blacklist_roles ?? [];
    return legacyMessage({ allowed_mentions: { parse: [] }, content: `Automatic game-role refresh: **${settings.auto_eval_status ? "On" : "Off"}**\nRole changes: **${settings.auto_eval_role_treatment === "add" ? "Add only" : settings.auto_eval_role_treatment === "remove" ? "Remove only" : "Both"}**\nAutomatic nicknames: **${settings.auto_eval_nickname ? "On" : "Off"}**\nExcluded member roles: ${roles.length ? roles.map(id => `<@&${id}>`).join(", ") : "None"}\nManual, roster and tenure refreshes are unaffected.`.slice(0, 1950) }, { ephemeral: true });
  },
};
