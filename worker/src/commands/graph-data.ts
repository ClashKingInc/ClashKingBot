import type { CommandContext } from "./types";
export const graphMetrics = {
  donated: "Donations",
  received: "Troops received",
  clanGames: "Clan Games points",
  capitalDonated: "Capital Gold donated",
  gold: "Gold looted",
  elixir: "Elixir looted",
  darkElixir: "Dark Elixir looted",
  attackWins: "Attack wins",
  activity: "Activity",
  troopLevels: "Troop / spell levels gained",
  heroLevels: "Hero / pet levels gained",
  warStars: "War stars",
  warsWon: "Wars won",
  warsSpun: "Wars started",
  capitalRaided: "Capital Gold raided",
  raidParticipants: "Average raid participants",
  capitalTrophies: "Capital trophies",
};
export const dailyMetrics = {
  activity: "Activity",
  troopLevels: "Troop / spell levels gained",
  heroLevels: "Hero / pet levels gained",
  equipmentLevels: "Equipment levels gained",
  townhallLevels: "Town Hall levels gained",
  bestTrophies: "Personal-best trophy gains",
  experienceLevels: "Experience levels gained",
  nameChanges: "Name changes",
  warPreferenceChanges: "War preference changes",
  donated: "Donations",
  received: "Troops received",
  clanGames: "Clan Games points",
  capitalDonated: "Capital Gold donated",
  clanMoves: "Joins and leaves",
};
export type GraphMetric = keyof typeof graphMetrics;
const contributions = new Set([
  "donated",
  "received",
  "clanGames",
  "capitalDonated",
]);
export const graphBasis = (metric: string) =>
  [
    "gold",
    "elixir",
    "darkElixir",
    "attackWins",
    "troopLevels",
    "heroLevels",
  ].includes(metric)
    ? "Latest stored clan members"
    : "Clan recorded on each event or war";
export async function graphTotal(
  ctx: CommandContext,
  tag: string,
  season: string,
  metric: GraphMetric,
  signal?: AbortSignal,
): Promise<{ season: string; value: number | null }> {
  const query = season === "current" ? {} : { season };
  if (!contributions.has(metric))
    return ctx.services.api.get<{ season: string; value: number | null }>(
      `/v2/bot/clans/${encodeURIComponent(tag)}/graph-total`,
      { ...query, metric },
      signal,
    );
  const data = await ctx.services.api.get<{
    season: string;
    truncated: boolean;
    items: Array<Record<string, number>>;
  }>(`/v2/bot/clans/${encodeURIComponent(tag)}/season-stats`, query, signal);
  return {
    season: data.season,
    value: data.truncated
      ? null
      : data.items.reduce((sum, row) => sum + row[metric]!, 0),
  };
}

export const validGraphValue = (metric: string, value: number) =>
  Number.isFinite(value) &&
  value >= 0 &&
  (metric === "raidParticipants" ? value <= 50 : Number.isSafeInteger(value));
