import { CommandInputError } from "./command-utils";
import { loadCurrentWar } from "./war-data";
import { invokingUserId, OptionType, stringOption } from "./command-utils";
import {
  emojis,
  isDailyLegend,
  fetchPlayer,
  gameReply,
  pagedGameReply,
  legendDay,
  linkedAccounts,
  playerAutocomplete,
  playerLabel,
  playerOption,
  resolvePlayerTag,
  subcommand,
  userOption,
} from "./game-common";
import { rankedBattleLimit } from "./ranked";
import type { Command, CommandContext } from "./types";
import { playerAccountsReply } from "./player-profile";
import { playerProfileReply } from "./player-profile-pages";

interface War {
  state: string;
  attacksPerMember?: number;
  clan: WarSide;
  opponent: WarSide;
}
interface WarSide {
  tag: string;
  members?: Array<{ tag: string; attacks?: unknown[] }>;
}
interface Raids {
  items: Array<{
    state: string;
    members?: Array<{
      tag: string;
      attacks: number;
      attackLimit: number;
      bonusAttackLimit: number;
    }>;
  }>;
}

export const playerCommand: Command = {
  deferred: true,
  definition: {
    name: "player",
    description: "Player profiles, linked accounts and remaining attacks",
    type: 1,
    integration_types: [0, 1],
    contexts: [0, 1, 2],
    options: [
      {
        name: "lookup",
        description: "Player overview, troops, upgrades and clan history",
        type: OptionType.Subcommand,
        options: [{ ...playerOption, required: false }, userOption],
      },
      {
        name: "accounts",
        description: "List linked accounts and their clans",
        type: OptionType.Subcommand,
        options: [userOption],
      },
      {
        name: "to-do",
        description:
          "Remaining attacks and observed Clan Games or Season Pass progress",
        type: OptionType.Subcommand,
        options: [
          userOption,
          {
            name: "clan_games_goal",
            description: "Clan Games target points (default 4000)",
            type: OptionType.Integer,
            min_value: 1,
            max_value: 10000,
          },
          {
            name: "season_goal",
            description: "Optional Season Pass target points",
            type: OptionType.Integer,
            min_value: 1,
            max_value: 100000,
          },
          {
            name: "show_completed",
            description: "Include completed attack and points goals",
            type: OptionType.Boolean,
          },
        ],
      },
    ],
  },
  autocomplete: playerAutocomplete,
  async execute(context) {
    const ctx = subcommand(context),
      emoji = await emojis(ctx);
    if (ctx.path[0] === "lookup") {
      if (stringOption(ctx, "player"))
        return playerProfileReply(
          ctx,
          await fetchPlayer(ctx, await resolvePlayerTag(ctx)),
          emoji,
        );
      const accounts = (await linkedAccounts(ctx)).filter(
        (account) => !account.hidden,
      );
      const first = accounts.sort(
        (a, b) => (b.town_hall ?? 0) - (a.town_hall ?? 0),
      )[0];
      if (!first)
        return gameReply(
          ctx,
          "Player lookup",
          "No visible linked accounts found. Choose a player tag or use /link.",
        );
      const options = new Map(ctx.options);
      options.set("__accounts_user", {
        name: "__accounts_user",
        type: OptionType.String,
        value: stringOption(ctx, "discord_user") ?? invokingUserId(ctx),
      });
      return playerProfileReply(
        { ...ctx, options },
        await fetchPlayer(ctx, first.player_tag),
        emoji,
      );
    }
    const accounts = (await linkedAccounts(ctx)).filter(
      (account) => !account.hidden,
    );
    if (!accounts.length)
      return gameReply(
        ctx,
        "Linked accounts",
        "No linked accounts found. Use /link to add an account.",
      );
    if (ctx.path[0] === "accounts") {
      return playerAccountsReply(ctx, accounts, emoji);
    }
    return todo(
      ctx,
      accounts.map((account) => account.player_tag),
    );
  },
};

async function todo(ctx: CommandContext, tags: string[]) {
  const emoji = await emojis(ctx),
    day = legendDay();
  const gamesGoal = Number(ctx.options.get("clan_games_goal")?.value ?? 4000),
    seasonGoal =
      ctx.options.get("season_goal")?.value === undefined
        ? undefined
        : Number(ctx.options.get("season_goal")?.value),
    showCompleted = ctx.options.get("show_completed")?.value === true;
  if (
    !Number.isInteger(gamesGoal) ||
    gamesGoal < 1 ||
    gamesGoal > 10000 ||
    (seasonGoal !== undefined &&
      (!Number.isInteger(seasonGoal) || seasonGoal < 1 || seasonGoal > 100000))
  )
    throw new CommandInputError("Choose valid points goals.");
  interface Progress {
    tag: string;
    clanGamesPoints: number | null;
    seasonPoints: number | null;
    lastCapitalDonation: string | null;
  }
  const progress = new Map<string, Progress>(),
    missingLegend = new Set<string>(),
    missingProgress = new Set<string>();
  let gamesActive = false;
  const days: { items: Array<{ tag: string; attacks: number }> } = {
    items: [],
  };
  for (let offset = 0; offset < tags.length; offset += 100) {
    const selected = tags.slice(offset, offset + 100);
    const [legendResult, taskResult] = await Promise.allSettled([
      ctx.services.api.post<typeof days>("/v2/legends/days", {
        day,
        tags: selected,
      }),
      ctx.services.api.post<{ clanGamesActive: boolean; items: Progress[] }>(
        "/v2/bot/players/task-progress",
        { tags: selected },
      ),
    ]);
    if (legendResult.status === "fulfilled")
      days.items.push(...legendResult.value.items);
    else selected.forEach((tag) => missingLegend.add(tag));
    if (taskResult.status === "fulfilled") {
      gamesActive = taskResult.value.clanGamesActive;
      taskResult.value.items.forEach((item) => progress.set(item.tag, item));
    } else selected.forEach((tag) => missingProgress.add(tag));
  }
  const clanWars = new Map<string, Promise<War | undefined>>(),
    clanRaids = new Map<string, Promise<Raids>>();
  async function war(clanTag: string): Promise<War | undefined> {
    const result = await loadCurrentWar(ctx, clanTag);
    return result.war?.state === "inWar" ? result.war : undefined;
  }
  const lines: string[] = [];
  // Bound upstream concurrency while sharing clan reads across linked accounts.
  for (let offset = 0; offset < tags.length; offset += 5) {
    lines.push(
      ...(await Promise.all(
        tags.slice(offset, offset + 5).map(async (tag) => {
          try {
            const player = await fetchPlayer(ctx, tag),
              chores: string[] = [];
            const summary = days.items.find((item) => item.tag === tag);
            const remaining = (left: number, total: number, label: string) => {
              if (left > 0 || showCompleted)
                chores.push(`${Math.max(0, left)}/${total} ${label}`);
            };
            if (isDailyLegend(player)) {
              if (missingLegend.has(tag))
                chores.push("Legend attacks unavailable");
              else
                remaining(
                  8 - (summary?.attacks ?? 0),
                  8,
                  "Legend attacks left",
                );
            } else if (
              player.currentLeagueGroupTag &&
              player.currentLeagueSeasonId
            ) {
              try {
                const [group, limit] = await Promise.all([
                  ctx.services.api.get<{
                    members: Array<{
                      playerTag: string;
                      attackWinCount: number;
                      attackLoseCount: number;
                    }>;
                  }>(
                    `/v2/bot/clash/leaguegroup/${encodeURIComponent(player.currentLeagueGroupTag)}/${player.currentLeagueSeasonId}`,
                    { playerTag: tag },
                  ),
                  rankedBattleLimit(player.leagueTier?.id ?? 0),
                ]);
                const member = group.members.find(
                  (item) => item.playerTag === tag,
                );
                if (member && limit !== undefined)
                  remaining(
                    limit - member.attackWinCount - member.attackLoseCount,
                    limit,
                    "Ranked attacks left",
                  );
                else chores.push("Ranked attacks unavailable");
              } catch {
                chores.push("Ranked attacks unavailable");
              }
            }
            if (player.clan) {
              const clanTag = player.clan.tag;
              if (!clanWars.has(clanTag)) clanWars.set(clanTag, war(clanTag));
              if (!clanRaids.has(clanTag))
                clanRaids.set(
                  clanTag,
                  ctx.services.api.get<Raids>(
                    `/v2/bot/clash/clans/${encodeURIComponent(clanTag)}/capitalraidseasons`,
                    { limit: 1 },
                  ),
                );
              const [warResult, raidResult] = await Promise.allSettled([
                clanWars.get(clanTag)!,
                clanRaids.get(clanTag)!,
              ]);
              if (warResult.status === "fulfilled") {
                const active = warResult.value,
                  member =
                    active &&
                    [active.clan, active.opponent]
                      .flatMap((side) => side.members ?? [])
                      .find((item) => item.tag === tag);
                if (member) {
                  const limit = active?.attacksPerMember ?? 1;
                  remaining(
                    limit - (member.attacks?.length ?? 0),
                    limit,
                    "war/CWL attacks left",
                  );
                }
              } else chores.push("War/CWL unavailable");
              if (raidResult.status === "fulfilled") {
                const raid = raidResult.value.items.find(
                    (item) => item.state === "ongoing",
                  ),
                  member = raid?.members?.find((item) => item.tag === tag);
                if (raid) {
                  const limit = member
                    ? member.attackLimit + member.bonusAttackLimit
                    : 5;
                  remaining(
                    limit - (member?.attacks ?? 0),
                    limit,
                    "raid attacks left",
                  );
                }
              } else chores.push("Raids unavailable");
            }
            const observed = progress.get(tag);
            if (gamesActive && player.townHallLevel >= 6) {
              if (observed?.clanGamesPoints == null)
                chores.push("Clan Games points unknown");
              else if (observed.clanGamesPoints < gamesGoal || showCompleted)
                chores.push(
                  `Clan Games ${observed.clanGamesPoints}/${gamesGoal} observed points`,
                );
            }
            if (seasonGoal !== undefined) {
              if (observed?.seasonPoints == null)
                chores.push("Season Pass points unknown");
              else if (observed.seasonPoints < seasonGoal || showCompleted)
                chores.push(
                  `Season Pass ${observed.seasonPoints}/${seasonGoal} observed points`,
                );
            }
            if (
              observed?.lastCapitalDonation &&
              Date.now() - Date.parse(observed.lastCapitalDonation) >= 86400000
            )
              chores.push(
                `Last recorded capital donation <t:${Math.floor(Date.parse(observed.lastCapitalDonation) / 1000)}:R>`,
              );
            if (missingProgress.has(tag))
              chores.push("Points progress unavailable");
            return `${emoji.get(player.townHallLevel)} ${playerLabel(player)}\n${chores.join(" · ") || "No remaining observed tasks."}`;
          } catch {
            return `${tag} · Player unavailable`;
          }
        }),
      )),
    );
  }
  return pagedGameReply(
    ctx,
    "Player to-do",
    lines,
    "pt",
    [
      stringOption(ctx, "discord_user") ?? invokingUserId(ctx),
      String(gamesGoal),
      seasonGoal === undefined ? "none" : String(seasonGoal),
      showCompleted ? "1" : "0",
    ],
    undefined,
    `Legend day ${day} · Observed points and attacks may lag the game`,
  );
}
