import { withClanSelector } from "./clan-controls";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType } from "../discord/types";
import {
  CommandInputError,
  OptionType,
  normalizeTag,
  requireGuildId,
  stringOption,
} from "./command-utils";
import { emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";

type Scope = "clan" | "family";
interface Member {
  tag: string;
  name: string;
  townHallLevel?: number;
  role?: string;
  trophies?: number;
  builderBaseTrophies?: number;
  versusTrophies?: number;
  expLevel?: number;
  donations?: number;
  donationsReceived?: number;
  warStars?: number;
  attackWins?: number;
  defenseWins?: number;
  clanCapitalContributions?: number;
  leagueTier?: { name: string };
  league?: { name: string };
  heroes?: Array<{ level: number }>;
  clan?: { tag: string };
}
interface Clan {
  tag: string;
  name: string;
  memberList: Member[];
}
const metrics: Record<
  string,
  { label: string; key: keyof Member; full?: boolean }
> = {
  townhall: { label: "Town Hall", key: "townHallLevel" },
  trophies: { label: "Trophies", key: "trophies" },
  builder_trophies: {
    label: "Builder Base trophies",
    key: "builderBaseTrophies",
  },
  experience: { label: "Experience level", key: "expLevel" },
  donated: { label: "Donated", key: "donations" },
  received: { label: "Received", key: "donationsReceived" },
  war_stars: { label: "War stars", key: "warStars", full: true },
  attack_wins: { label: "Attack wins", key: "attackWins", full: true },
  defense_wins: { label: "Defense wins", key: "defenseWins", full: true },
  capital: {
    label: "Capital contributions",
    key: "clanCapitalContributions",
    full: true,
  },
  heroes: { label: "Total hero levels", key: "heroes", full: true },
};
const groups = {
  townhall: "Town Hall",
  trophies: "Trophy bands",
  role: "Clan role",
  league: "Ranked league",
  location: "Ranking location",
};
export function memberReportOptions(
  action: "compo" | "sorted",
): ApplicationCommandOption[] {
  return [
    action === "compo"
      ? {
          name: "type",
          description: "Group members by (default Town Hall)",
          type: OptionType.String,
          choices: Object.entries(groups).map(([value, name]) => ({
            name,
            value,
          })),
        }
      : {
          name: "sort_by",
          description: "Member statistic to sort by",
          type: OptionType.String,
          required: true,
          choices: Object.entries(metrics).map(([value, { label: name }]) => ({
            name,
            value,
          })),
        },
    {
      name: "townhall",
      description: "Only this Town Hall",
      type: OptionType.Integer,
      min_value: 1,
      max_value: 30,
    },
    {
      name: "limit",
      description: "Rows to show (default 30)",
      type: OptionType.Integer,
      min_value: 1,
      max_value: 50,
    },
    {
      name: "sort_order",
      description: "Direction (default Highest first)",
      type: OptionType.String,
      choices: [
        { name: "Highest first", value: "desc" },
        { name: "Lowest first", value: "asc" },
      ],
    },
  ];
}
export async function memberReport(ctx: CommandContext, scope: Scope) {
  const action = ctx.path[0],
    metric =
      stringOption(ctx, action === "compo" ? "type" : "sort_by") ?? "townhall",
    hall = Number(ctx.options.get("townhall")?.value ?? 0),
    limit = Number(ctx.options.get("limit")?.value ?? 30),
    order = stringOption(ctx, "sort_order") ?? "desc";
  if (
    !["compo", "sorted"].includes(action ?? "") ||
    !(action === "compo" ? metric in groups : metric in metrics) ||
    !Number.isInteger(hall) ||
    hall < 0 ||
    hall > 30 ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 50 ||
    !["asc", "desc"].includes(order)
  )
    throw new CommandInputError("Choose valid member report options.");
  const target =
    scope === "clan"
      ? normalizeTag(stringOption(ctx, "clan") ?? "", ctx.locale)
      : requireGuildId(ctx);
  const refs =
    scope === "clan"
      ? [{ tag: target }]
      : await ctx.services.api.get<Array<{ tag: string }>>(
          `/v2/server/${target}/clans-basic`,
        );
  if (!refs.length) throw new CommandInputError("No family clans are linked to this server.");
  if (refs.length > 200)
    throw new CommandInputError("This report supports up to 200 linked clans.");
  const clans: Clan[] = [];
  let failedClans = 0,
    failedPlayers = 0;
  for (let i = 0; i < refs.length; i += 5) {
    const results = await Promise.allSettled(
      refs
        .slice(i, i + 5)
        .map((clan) =>
          ctx.services.api.get<Clan>(
            `/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}`,
          ),
        ),
    );
    for (const result of results) {
      if (result.status === "fulfilled") clans.push(result.value);
      else failedClans++;
    }
  }
  const unique = new Map<string, Member>();
  for (const clan of clans)
    for (const member of clan.memberList) unique.set(member.tag, member);
  let members = [...unique.values()];
  if (action === "sorted" && metrics[metric]?.full) {
    const loaded: Member[] = [];
    for (let i = 0; i < members.length; i += 5) {
      const results = await Promise.allSettled(
        members
          .slice(i, i + 5)
          .map((member) =>
            ctx.services.api.get<Member>(
              `/v2/bot/clash/players/${encodeURIComponent(member.tag)}`,
            ),
          ),
      );
      for (const result of results) {
        if (result.status === "fulfilled") loaded.push(result.value);
        else failedPlayers++;
      }
    }
    members = loaded;
  }
  members = members.filter((member) => !hall || member.townHallLevel === hall);
  const emoji = await emojis(ctx),
    color = await serverEmbedColor(ctx);
  let rows: string[], label: string;
  if (action === "compo") {
    const countries = new Map<string, string>();
    if (metric === "location")
      for (let i = 0; i < members.length; i += 100) {
        const result = await ctx.services.api.post<{
          items: Array<{ tag: string; location?: { name: string } }>;
        }>("/v2/legends/ranks", {
          tags: members.slice(i, i + 100).map((member) => member.tag),
        });
        for (const item of result.items)
          if (item.location?.name) countries.set(item.tag, item.location.name);
      }
    const buckets = new Map<string, number>();
    for (const member of members) {
      let key: string;
      if (metric === "townhall")
        key = String(member.townHallLevel ?? "Unknown");
      else if (metric === "trophies")
        key =
          typeof member.trophies === "number"
            ? String(Math.floor(member.trophies / 500) * 500)
            : "Unknown";
      else if (metric === "role") key = member.role ?? "Unknown";
      else if (metric === "league")
        key = member.leagueTier?.name ?? member.league?.name ?? "Unranked";
      else key = countries.get(member.tag) ?? "Unknown";
      buckets.set(key, (buckets.get(key) ?? 0) + 1);
    }
    rows = [...buckets]
      .sort((a, b) => {
        const cmp = ["townhall", "trophies"].includes(metric)
          ? Number(a[0]) - Number(b[0])
          : a[1] - b[1];
        return (order === "asc" ? cmp : -cmp) || a[0].localeCompare(b[0]);
      })
      .map(([key, count]) => {
        const name =
          metric === "townhall" && key !== "Unknown"
            ? `${emoji.get(Number(key))} TH${key}`
            : metric === "trophies" && key !== "Unknown"
              ? `${key}–${Number(key) + 499}`
              : escapeMarkdown(key);
        return `**${name}** · ${count} · ${members.length ? ((count / members.length) * 100).toFixed(1) : 0}%`;
      });
    label = groups[metric as keyof typeof groups];
  } else {
    const rule = metrics[metric]!;
    label = rule.label;
    const value = (member: Member) =>
      metric === "heroes"
        ? member.heroes?.reduce((sum, hero) => sum + hero.level, 0)
        : metric === "builder_trophies"
          ? (member.builderBaseTrophies ?? member.versusTrophies)
          : member[rule.key];
    const measured = members.flatMap((member) => {
      const number = value(member);
      return typeof number === "number" && Number.isFinite(number)
        ? [{ member, number }]
        : [];
    });
    failedPlayers += members.length - measured.length;
    measured.sort(
      (a, b) =>
        (order === "asc" ? 1 : -1) * (a.number - b.number) ||
        a.member.tag.localeCompare(b.member.tag),
    );
    rows = measured.map(
      ({ member, number }, index) =>
        `**${index + 1}.** ${emoji.get(member.townHallLevel ?? 0)} ${escapeMarkdown(member.name)} · **${number.toLocaleString("en")}**`,
    );
  }
  let description = "",
    shown = 0;
  for (const line of rows.slice(0, limit)) {
    if (description.length + line.length + 1 > 3600) break;
    description += (description ? "\n" : "") + line;
    shown++;
  }
  const title = `${scope === "family" ? "Family" : (clans[0]?.name ?? "Clan")} · ${label}`;
  const footer = `${shown}/${rows.length} ${action === "compo" ? "groups" : "players"} · ${members.length} members${failedClans ? ` · ${failedClans} clans unavailable` : ""}${failedPlayers ? ` · ${failedPlayers} profiles/stats unavailable` : ""}${metric === "location" ? " · Public ranking location only" : ""}`;
  const icon = emoji.component("refresh");
  const response = legacyMessage({
    allowed_mentions: { parse: [] },
    embeds: [
      {
        title,
        color,
        description: description || (failedClans || failedPlayers ? "Member data is unavailable. Try again." : "No members match these filters."),
        footer: { text: footer },
      },
    ],
    components: [
      actionRow({
        type: 2,
        style: 2,
        label: "Refresh",
        ...(icon ? { emoji: icon } : {}),
        custom_id: `ck:members:${scope}|${target}|${action}|${metric}|${hall}|${limit}|${order}`,
      }),
    ],
  });
  return scope === "clan" ? withClanSelector(ctx, response) : response;
}
export async function dispatchMemberReport(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
) {
  const parts = (ctx.interaction.data?.custom_id ?? "")
    .slice("ck:members:".length)
    .split("|");
  const [scope, target, action, metric, hall, limit, order] = parts;
  if (
    parts.length !== 7 ||
    !["clan", "family"].includes(scope ?? "") ||
    (scope === "family" && target !== ctx.interaction.guild_id)
  )
    throw new CommandInputError("Invalid member report.");
  const options = new Map(ctx.options);
  for (const [name, value] of [
    ["clan", target],
    [action === "compo" ? "type" : "sort_by", metric],
    ["sort_order", order],
  ] as const)
    options.set(name, { name, type: OptionType.String, value });
  options.set("townhall", {
    name: "townhall",
    type: OptionType.Integer,
    value: Number(hall),
  });
  options.set("limit", {
    name: "limit",
    type: OptionType.Integer,
    value: Number(limit),
  });
  const run = memberReport(
    { ...ctx, path: [action!], options },
    scope as Scope,
  );
  if (!waitUntil) return run;
  waitUntil(
    run
      .then((reply) =>
        ctx.services.discordRest.editOriginalInteractionResponse(
          ctx.interaction.token,
          reply.data ?? {},
        ),
      )
      .catch(() =>
        ctx.services.discordRest.createInteractionFollowup(
          ctx.interaction.token,
          { content: "Could not refresh this report. Try again.", flags: 64 },
        ),
      ),
  );
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
