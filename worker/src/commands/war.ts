import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType } from "../discord/types";
import {
  CommandInputError,
  OptionType,
  normalizeTag,
  stringOption,
} from "./command-utils";
import { familyCwl, familyCwlOptions } from "./cwl-family";
import { clanCommand } from "./clan";
import { emojis, escapeMarkdown, subcommand } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import {
  clanRounds,
  cwlRanking,
  compactWarTime,
  isWar,
  latestWar,
  loadCurrentWar,
  loadCwl,
  warTime,
  type War,
  type WarSide,
} from "./war-data";
import type { Command, CommandContext } from "./types";

const clanOption = {
  name: "clan",
  description: "Clan tag or name",
  type: OptionType.String,
  required: true,
  autocomplete: true,
};
const viewOption = {
  name: "view",
  description: "What to show (default Overview)",
  type: OptionType.String,
  choices: [
    { name: "Overview", value: "overview" },
    { name: "Attacks", value: "attacks" },
    { name: "Defenses", value: "defenses" },
    { name: "Roster", value: "roster" },
    { name: "Opponent roster", value: "opponent" },
  ],
};
const limitOption = {
  name: "limit",
  description: "Maximum player rows (default 30)",
  type: OptionType.Integer,
  min_value: 1,
  max_value: 50,
};
const views = ["overview", "attacks", "defenses", "roster", "opponent"];
interface ClanInfo {
  name: string;
  isWarLogPublic?: boolean;
  badgeUrls?: { small?: string };
}

export const warCommand: Command = {
  deferred: true,
  definition: {
    name: "war",
    description: "Current or recorded clan wars",
    type: 1,
    integration_types: [0, 1],
    contexts: [0, 1, 2],
    options: [
      {
        name: "search",
        description: "Show a clan's current or recorded war",
        type: OptionType.Subcommand,
        options: [
          clanOption,
          {
            name: "war_end",
            description: "Recorded war end time (pick a suggestion)",
            type: OptionType.String,
            autocomplete: true,
          },
          viewOption,
          limitOption,
        ],
      },
    ],
  },
  async autocomplete(context) {
    const ctx = subcommand(context);
    if (ctx.options.get("war_end")?.focused) {
      const raw = stringOption(ctx, "clan");
      if (!raw) return [];
      const tag = normalizeTag(raw, ctx.locale);
      const data = await ctx.services.api.get<{ items: War[] }>(
        `/v2/clan/${encodeURIComponent(tag)}/wars`,
        { limit: 25 },
      );
      return data.items
        .filter((war) => isWar(war, tag))
        .map((war) => ({
          name: `${new Date(warTime(war.endTime)).toISOString().slice(0, 10)} · ${war.clan.tag === tag ? war.opponent.name : war.clan.name}`.slice(
            0,
            100,
          ),
          value: compactWarTime(war.endTime),
        }));
    }
    return clanCommand.autocomplete!(context);
  },
  async execute(context) {
    const ctx = subcommand(context),
      tag = normalizeTag(stringOption(ctx, "clan") ?? "", ctx.locale),
      end = stringOption(ctx, "war_end") ?? "current";
    if (
      end !== "current" &&
      (!/^\d{8}T\d{6}\.\d{3}Z$/u.test(end) ||
        !Number.isFinite(warTime(end)) ||
        compactWarTime(end) !== end)
    )
      throw new CommandInputError("Choose a recorded war end time.");
    const settings = readSettings(ctx),
      clan = await ctx.services.api.get<ClanInfo>(
        `/v2/bot/clash/clans/${encodeURIComponent(tag)}`,
      );
    if (end !== "current") {
      const war = await ctx.services.api.get<War>(
        `/v2/war/${encodeURIComponent(tag)}/previous/${end}`,
      );
      if (!isWar(war, tag))
        throw new CommandInputError(
          "That recorded war does not contain this clan.",
        );
      return warReply(ctx, tag, war, false, end, settings);
    }
    const result = await loadCurrentWar(ctx, tag);
    if (!result.war)
      return legacyMessage({
        embeds: [
          {
            title: clan.name,
            description:
              result.privateLog || clan.isWarLogPublic === false
                ? "The war log is private and no matching war is available."
                : "No active war is available.",
            color: await serverEmbedColor(ctx),
          },
        ],
        components: await controls(ctx, "war", tag, end, settings),
      });
    return warReply(ctx, tag, result.war, result.cwl, end, settings);
  },
};
export const cwlCommand: Command = {
  deferred: true,
  definition: {
    name: "cwl",
    description: "Clan War League rounds and standings",
    type: 1,
    integration_types: [0, 1],
    contexts: [0, 1, 2],
    options: [
      {
        name: "rankings",
        description: "CWL standings across linked family clans",
        type: OptionType.Subcommand,
        options: [
          ...familyCwlOptions,
          {
            name: "season",
            description: "Season YYYY-MM (defaults to current)",
            type: OptionType.String,
          },
        ],
      },
      {
        name: "status",
        description: "CWL group status across linked family clans",
        type: OptionType.Subcommand,
        options: familyCwlOptions,
      },
      {
        name: "search",
        description: "Show current or recorded Clan War League rounds",
        type: OptionType.Subcommand,
        options: [
          clanOption,
          {
            name: "season",
            description: "Season YYYY-MM (defaults to current)",
            type: OptionType.String,
          },
          {
            name: "round",
            description: "Show one round instead of group standings",
            type: OptionType.Integer,
            min_value: 1,
            max_value: 7,
          },
          viewOption,
          limitOption,
        ],
      },
    ],
  },
  autocomplete: (context) => clanCommand.autocomplete!(context),
  async execute(context) {
    const ctx = subcommand(context);
    if (["rankings", "status"].includes(ctx.path[0] ?? ""))
      return familyCwl(ctx);
    const tag = normalizeTag(stringOption(ctx, "clan") ?? "", ctx.locale),
      season = stringOption(ctx, "season") ?? "current",
      settings = readSettings(ctx),
      round = Number(ctx.options.get("round")?.value ?? 0);
    if (season !== "current" && !/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))
      throw new CommandInputError("Use a season in YYYY-MM format.");
    if (!Number.isInteger(round) || round < 0 || round > 7)
      throw new CommandInputError("Choose a round from 1 to 7.");
    const result = await loadCwl(
      ctx,
      tag,
      season === "current" ? undefined : season,
    );
    if (!result)
      return legacyMessage({
        content:
          "No Clan War League group is available for that clan and season.",
        components: await controls(ctx, "cwl", tag, season, settings, round),
      });
    const roundsByIndex = clanRounds(result.group, result.wars, tag);
    const own = roundsByIndex.filter((war): war is War => war !== undefined);
    if (round || settings.view !== "overview") {
      const war = round ? roundsByIndex[round - 1] : latestWar(own, tag);
      if (!war)
        throw new CommandInputError(
          "That round's war data is not available yet.",
        );
      return warReply(ctx, tag, war, true, season, settings, "cwl", round);
    }
    const ranked = cwlRanking(result.group, result.wars);
    const emoji = await emojis(ctx),
      standing = ranked
        .map(
          ([clan, score]) =>
            `**${score.rank}. ${escapeMarkdown(score.name)}${clan === tag ? " ←" : ""}** · ${emoji.get("war_star")} ${score.stars}`,
        )
        .join("\n");
    const rounds =
      roundsByIndex
        .map((war, i) => {
          if (!war) return `**${i + 1}.** War data not available yet.`;
          const side = war.clan.tag === tag ? war.clan : war.opponent,
            other = side === war.clan ? war.opponent : war.clan;
          return `**${i + 1}.** ${escapeMarkdown(other.name)} · ${war.state === "preparation" ? "Preparation" : `${side.stars}–${other.stars} stars`}${war.state === "inWar" ? " · In war" : ""}`;
        })
        .join("\n") || "No round data recorded yet.";
    return legacyMessage({
      allowed_mentions: { parse: [] },
      embeds: [
        {
          title: `Clan War League · ${result.group.season}`,
          description: standing,
          color: await serverEmbedColor(ctx),
          fields: [{ name: "Clan rounds", value: rounds }],
          footer: {
            text: "10 bonus stars only for completed wins · standings may be provisional",
          },
        },
      ],
      components: await controls(ctx, "cwl", tag, season, settings),
    });
  },
};
function readSettings(ctx: CommandContext) {
  const view = stringOption(ctx, "view") ?? "overview",
    limit = Number(ctx.options.get("limit")?.value ?? 30);
  if (
    !views.includes(view) ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 50
  )
    throw new CommandInputError("Choose a valid view and row limit.");
  return { view, limit };
}
async function controls(
  ctx: CommandContext,
  kind: string,
  tag: string,
  period: string,
  settings: { view: string; limit: number },
  round = 0,
) {
  const icon = (await emojis(ctx)).component("refresh");
  return [
    actionRow({
      type: 2,
      style: 2,
      label: "Refresh",
      ...(icon ? { emoji: icon } : {}),
      custom_id: `ck:war:${kind}|${tag}|${period}|${settings.view}|${settings.limit}|${round}`,
    }),
  ];
}
async function warReply(
  ctx: CommandContext,
  tag: string,
  war: War,
  cwl: boolean,
  period: string,
  settings: { view: string; limit: number },
  kind = "war",
  round = 0,
) {
  const own = war.clan.tag === tag ? war.clan : war.opponent,
    other = own === war.clan ? war.opponent : war.clan,
    emoji = await emojis(ctx),
    maximum = war.teamSize * (war.attacksPerMember ?? (cwl ? 1 : 2));
  const date = war.state === "preparation" ? war.startTime : war.endTime,
    when =
      date && Number.isFinite(warTime(date))
        ? `<t:${Math.floor(warTime(date) / 1000)}:R>`
        : "time unavailable";
  let description: string;
  if (settings.view === "overview") {
    const count = (side: WarSide) =>
      side.members.reduce((n, p) => n + (p.attacks?.length ?? 0), 0);
    description = `**${escapeMarkdown(own.name)} vs ${escapeMarkdown(other.name)}**\n${own.stars} ${emoji.get("war_star")} ${other.stars}\n${own.destructionPercentage.toFixed(2)}% · ${other.destructionPercentage.toFixed(2)}%\nAttacks: ${count(own)}/${maximum} · ${count(other)}/${maximum}\n${war.state === "preparation" ? "Starts" : war.state === "warEnded" ? "Ended" : "Ends"} ${when}`;
  } else {
    const side = settings.view === "opponent" ? other : own,
      opponents = new Map(
        [...own.members, ...other.members].map((p) => [p.tag, p]),
      );
    const lines = side.members
      .slice()
      .sort((a, b) => a.mapPosition - b.mapPosition)
      .slice(0, settings.limit)
      .map((member) => {
        const head = `**#${member.mapPosition} ${escapeMarkdown(member.name)}** · TH${member.townhallLevel}`;
        if (["roster", "opponent"].includes(settings.view)) return head;
        const attacks =
          settings.view === "attacks"
            ? (member.attacks ?? [])
            : other.members
                .flatMap((p) => p.attacks ?? [])
                .filter((a) => a.defenderTag === member.tag);
        return (
          head +
          "\n" +
          (attacks.length
            ? attacks
                .map(
                  (a) =>
                    `${a.stars}${emoji.get("war_star")} ${a.destructionPercentage}% · #${opponents.get(settings.view === "attacks" ? a.defenderTag : a.attackerTag)?.mapPosition ?? "?"}`,
                )
                .join("; ")
            : settings.view === "attacks"
              ? "No attacks used"
              : "No defense recorded")
        );
      });
    description = lines.join("\n\n");
    if (side.members.length > settings.limit)
      description += `\n\nShowing ${settings.limit}/${side.members.length} players.`;
  }
  if (description.length > 3800)
    description =
      description.slice(0, 3750) +
      "\n… Use a smaller row limit to view the full entries.";
  return legacyMessage({
    allowed_mentions: { parse: [] },
    embeds: [
      {
        title: `${cwl ? "CWL" : "War"} · ${settings.view}`,
        description,
        color: await serverEmbedColor(ctx),
        ...(own.badgeUrls?.large
          ? { thumbnail: { url: own.badgeUrls.large } }
          : {}),
        footer: {
          text: `${war.teamSize}v${war.teamSize} · ${war.state}${round ? ` · Round ${round}` : ""}`,
        },
      },
    ],
    components: await controls(ctx, kind, tag, period, settings, round),
  });
}
export async function dispatchWar(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
) {
  const parts = (ctx.interaction.data?.custom_id ?? "")
    .slice("ck:war:".length)
    .split("|");
  const [kind, clan, period, view, limit, round] = parts;
  if (parts.length === 6 && kind === "family") {
    if (
      clan !== ctx.interaction.guild_id ||
      !["rankings", "status"].includes(period ?? "")
    )
      throw new CommandInputError("This report belongs to a different server.");
    const run = familyCwl({
      ...ctx,
      path: [period!],
      options: new Map([
        ["season", { name: "season", type: OptionType.String, value: view }],
        [
          "limit",
          { name: "limit", type: OptionType.Integer, value: Number(limit) },
        ],
        [
          "sort_order",
          { name: "sort_order", type: OptionType.String, value: round },
        ],
      ]),
    });
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
            {
              content: "Could not refresh this family report. Try again.",
              flags: 64,
            },
          ),
        ),
    );
    return { type: InteractionResponseType.DeferredUpdateMessage };
  }
  if (
    parts.length !== 6 ||
    !["war", "cwl"].includes(kind ?? "") ||
    !clan ||
    !period
  )
    throw new CommandInputError("Invalid war control.");
  const options = [
    { name: "clan", type: OptionType.String, value: clan },
    {
      name: kind === "war" ? "war_end" : "season",
      type: OptionType.String,
      value: period,
    },
    { name: "view", type: OptionType.String, value: view },
    { name: "limit", type: OptionType.Integer, value: Number(limit) },
    { name: "round", type: OptionType.Integer, value: Number(round) },
  ];
  const command = kind === "war" ? warCommand : cwlCommand;
  const run = command.execute({
    ...ctx,
    options: new Map([
      ["search", { name: "search", type: OptionType.Subcommand, options }],
    ]),
  });
  if (!waitUntil) return run;
  waitUntil(
    run
      .then((reply) =>
        ctx.services.discordRest.editOriginalInteractionResponse(
          ctx.interaction.token,
          reply.data ?? {},
        ),
      )
      .catch((error) =>
        ctx.services.discordRest.createInteractionFollowup(
          ctx.interaction.token,
          {
            content:
              error instanceof CommandInputError
                ? error.message
                : "Could not refresh this war. Try again.",
            flags: 64,
          },
        ),
      ),
  );
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
