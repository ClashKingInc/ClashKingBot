import { actionRow, legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, stringOption } from "./command-utils";
import { emojis, escapeMarkdown, playerLabel } from "./game-common";
import { playerCatalog } from "./player-catalog";
import { currentReportMembers } from "./report-members";
import { serverEmbedColor } from "./embed-color";
import { clanCommand } from "./clan";
import type { Command, CommandContext } from "./types";

const clean = (value: string) => escapeMarkdown(value.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu, "")).slice(0, 70);
export const boostsCommand: Command = {
  deferred: true,
  definition: { name: "boosts", description: "Find active Super Troops in a clan or linked family", type: 1, options: [
    { name: "clan", description: "Clan tag (defaults to this server's linked family)", type: OptionType.String, autocomplete: true },
    { name: "super_troop", description: "Only show this active Super Troop", type: OptionType.String, autocomplete: true, max_length: 40 },
    { name: "limit", description: "Maximum players to show (default 30)", type: OptionType.Integer, min_value: 1, max_value: 50 },
    { name: "sort_order", description: "Player name order (default ascending)", type: OptionType.String, choices: [{ name: "Ascending", value: "asc" }, { name: "Descending", value: "desc" }] },
  ] },
  async autocomplete(ctx) {
    if (ctx.options.get("super_troop")?.focused) {
      const query = String(ctx.options.get("super_troop")?.value ?? "").toLowerCase();
      return ((await playerCatalog()).get("troops") ?? []).filter(item => item.super_troop != null && item.name.toLowerCase().includes(query)).slice(0, 25).map(item => ({ name: item.name, value: item.name }));
    }
    return clanCommand.autocomplete!({ ...ctx, options: new Map([["search", { name: "search", type: OptionType.Subcommand, options: [...ctx.options.values()] }]]) });
  },
  execute: activeBoosts,
};

async function activeBoosts(ctx: CommandContext) {
  const raw = stringOption(ctx, "clan"), troop = stringOption(ctx, "super_troop") ?? "", limit = Number(ctx.options.get("limit")?.value ?? 30), order = stringOption(ctx, "sort_order") ?? "asc";
  if (!Number.isInteger(limit) || limit < 1 || limit > 50 || !["asc", "desc"].includes(order) || troop.length > 40 || (troop && !/^[A-Za-z '-]+$/u.test(troop))) throw new CommandInputError("Choose valid boost filters.");
  const scope = raw ? "clan" : "family", target = raw ? normalizeTag(raw, ctx.locale) : "-";
  const report = await currentReportMembers(ctx, scope);
  const clanNames = new Map(report.clans.map(clan => [clan.tag, clan.name]));
  const rows: Array<{ tag: string; name: string; clan: string; troops: string[] }> = [];
  let next = 0, checked = 0, unavailable = 0;
  const deadline = AbortSignal.timeout(12_000);
  // Snapshot membership can lag a transfer. Only a current profile in one of
  // the requested clans establishes an active boost; failures never mean none.
  await Promise.all(Array.from({ length: Math.min(8, report.members.length) }, async () => {
    while (next < report.members.length && !deadline.aborted) {
      const member = report.members[next++]!;
      try {
        const player = await ctx.services.api.get<{ tag: string; name: string; clan?: { tag: string; name: string }; troops?: Array<{ name: string; superTroopIsActive?: boolean }> }>(`/v2/bot/clash/players/${encodeURIComponent(member.tag)}`, {}, deadline);
        if (!Array.isArray(player.troops)) { unavailable++; continue; }
        checked++;
        if (!player.clan || !clanNames.has(player.clan.tag)) continue;
        const active = [...new Set(player.troops.filter(unit => unit.superTroopIsActive === true && (!troop || unit.name.toLowerCase() === troop.toLowerCase())).map(unit => unit.name))].sort();
        if (active.length) rows.push({ tag: player.tag, name: player.name, clan: player.clan.name, troops: active });
      } catch { unavailable++; }
    }
  }));
  unavailable += report.members.length - next;
  rows.sort((a, b) => (order === "asc" ? 1 : -1) * (a.name.localeCompare(b.name) || a.tag.localeCompare(b.tag)));
  const [icons, color] = await Promise.all([emojis(ctx), serverEmbedColor(ctx)]);
  let description = "", shown = 0;
  for (const row of rows.slice(0, limit)) {
    const line = `${playerLabel({ tag: row.tag, name: row.name.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu, "").slice(0, 70) })}${scope === "family" ? ` · ${clean(row.clan)}` : ""}\n${row.troops.map(name => `${icons.get(name)} ${clean(name)}`).join(" · ")}`;
    if (description.length + line.length + 2 > 3500) break;
    description += (description ? "\n\n" : "") + line; shown++;
  }
  const customId = ["ck", "page", "bs", invokingUserId(ctx), target, troop.replaceAll(" ", "~") || "-", limit, order, "0"].join(":");
  if (customId.length > 100) throw new CommandInputError("The troop filter is too long.");
  return legacyMessage({ allowed_mentions: { parse: [] }, embeds: [{
    title: `${scope === "clan" ? clean(report.clans[0]?.name ?? "Clan") : "Family"} · ${troop ? clean(troop) : "Active Super Troops"}`,
    color, description: description || (unavailable || report.failedClans ? "No active boosts found in the available profiles. Coverage is incomplete." : "No active boosts found."),
    footer: { text: `${shown}/${rows.length} boosted players shown · ${checked}/${report.members.length} profiles checked${unavailable ? ` · ${unavailable} unavailable` : ""}${report.failedClans ? ` · ${report.failedClans} clans unavailable` : ""}` },
  }], components: [actionRow({ type: 2, style: 2, label: "Refresh", custom_id: customId })] });
}
