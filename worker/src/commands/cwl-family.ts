import { actionRow, legacyMessage } from "../discord/components";
import {
  CommandInputError,
  OptionType,
  requireGuildId,
  stringOption,
} from "./command-utils";
import { emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { cwlRanking, cwlStatus, loadCwl, type War } from "./war-data";
import type { ApplicationCommandOption, CommandContext } from "./types";

export const familyCwlOptions: ApplicationCommandOption[] = [
  {
    name: "limit",
    description: "Clan rows to show (default 30)",
    type: OptionType.Integer,
    min_value: 1,
    max_value: 50,
  },
  {
    name: "sort_order",
    description: "League order (default Highest first)",
    type: OptionType.String,
    choices: [
      { name: "Highest first", value: "desc" },
      { name: "Lowest first", value: "asc" },
    ],
  },
];
interface Clan {
  name: string;
  tag: string;
  warLeague?: { id: number; name: string };
}
interface Row {
  clan: Clan;
  state?: string;
  rank?: number;
  stars?: number;
  unavailable?: boolean;
}
export async function familyCwl(ctx: CommandContext) {
  const guild = requireGuildId(ctx),
    action = ctx.path[0],
    limit = Number(ctx.options.get("limit")?.value ?? 30),
    order = stringOption(ctx, "sort_order") ?? "desc",
    season = stringOption(ctx, "season") ?? "current";
  if (
    !["rankings", "status"].includes(action ?? "") ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 50 ||
    !["asc", "desc"].includes(order) ||
    (season !== "current" && !/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))
  )
    throw new CommandInputError("Choose valid CWL report options.");
  const linked = await ctx.services.api.get<
    Array<{ tag: string; name: string }>
  >(`/v2/server/${guild}/clans-basic`);
  if (!linked.length)
    throw new CommandInputError("No family clans are linked to this server.");
  if (linked.length > 200)
    throw new CommandInputError(
      "This family is too large for one CWL report (maximum 200 clans).",
    );
  const rows: Row[] = [],
    warCache = new Map<string, Promise<War[]>>();
  for (let i = 0; i < linked.length; i += 4)
    rows.push(
      ...(await Promise.all(
        linked.slice(i, i + 4).map(async (reference) => {
          let clan: Clan = { ...reference };
          try {
            clan = await ctx.services.api.get<Clan>(
              `/v2/bot/clash/clans/${encodeURIComponent(reference.tag)}`,
            );
            if (action === "status")
              return { clan, state: await cwlStatus(ctx, clan.tag) };
            const data = await loadCwl(
              ctx,
              clan.tag,
              season === "current" ? undefined : season,
              warCache,
            );
            if (data?.group.warLeague)
              clan = {
                ...clan,
                warLeague: {
                  id: data.group.warLeague.id ?? 0,
                  name: data.group.warLeague.name,
                },
              };
            const score =
              data &&
              cwlRanking(data.group, data.wars).find(
                ([tag]) => tag === clan.tag,
              )?.[1];
            return {
              clan,
              ...(score && data.wars.length
                ? { rank: score.rank, stars: score.stars }
                : { state: "No available group" }),
            };
          } catch {
            return { clan, unavailable: true };
          }
        }),
      )),
    );
  rows.sort((a, b) => {
    const league = (a.clan.warLeague?.id ?? 0) - (b.clan.warLeague?.id ?? 0);
    return (
      (order === "desc" ? -league : league) ||
      (a.rank ?? Infinity) - (b.rank ?? Infinity) ||
      a.clan.name.localeCompare(b.clan.name)
    );
  });
  const emoji = await emojis(ctx),
    states: Record<string, string> = {
      inWar: "In war",
      preparation: "Preparation",
      ended: "Ended",
      warEnded: "Ended",
      notInWar: "Not participating",
      unavailable: "No available group",
    };
  let description = "",
    shown = 0;
  for (const row of rows.slice(0, limit)) {
    const detail = row.unavailable
      ? "Unavailable — retry later"
      : action === "status"
        ? (states[row.state ?? ""] ?? row.state ?? "Unknown")
        : row.rank
          ? `Group rank #${row.rank} · ${row.stars} stars`
          : row.state;
    const line = `**${escapeMarkdown(row.clan.name)}** · ${escapeMarkdown(row.clan.warLeague?.name ?? "Unranked")}\n${detail}`;
    if (description.length + line.length + 2 > 3800) break;
    description += (description ? "\n\n" : "") + line;
    shown++;
  }
  const refresh = emoji.component("refresh");
  return legacyMessage({
    allowed_mentions: { parse: [] },
    embeds: [
      {
        title: `Family CWL ${action}`,
        description,
        color: await serverEmbedColor(ctx),
        footer: {
          text: `${season === "current" ? new Date().toISOString().slice(0, 7) : season} · ${shown}/${rows.length} clans · ${action === "rankings" ? "Standings may be provisional" : "Current group status"}`,
        },
      },
    ],
    components: [
      actionRow({
        type: 2,
        style: 2,
        label: "Refresh",
        ...(refresh ? { emoji: refresh } : {}),
        custom_id: `ck:war:family|${guild}|${action}|${season}|${limit}|${order}`,
      }),
    ],
  });
}
