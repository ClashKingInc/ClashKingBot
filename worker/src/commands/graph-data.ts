import type { CommandContext } from "./types";
export const graphMetrics = {
  clanMoves: "Joins and leaves",
  donated: "Donations",
  received: "Troops received",
  capitalDonated: "Capital Gold donated",
  gold: "Gold looted",
  elixir: "Elixir looted",
  darkElixir: "Dark Elixir looted",
  activity: "Activity",
  upgrades: "Upgrades",
  warStars: "War stars",
  warWinRate: "War win rate",
  cwlLeague: "CWL league",
  warsWon: "Wars won",
  warsSpun: "Wars started",
  capitalRaided: "Capital Gold raided",
};
export const dailyMetrics = {
  activity: "Activity",
  upgrades: "Upgrades",
  donated: "Donations",
  received: "Troops received",
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
    "upgrades",
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
  (metric === "raidParticipants" ? value <= 50 : metric === "warWinRate" ? value <= 100 : Number.isSafeInteger(value));

export const graphMetricIcons:Record<string,string>={activity:'clock',upgrades:'Barbarian King',donated:'up_green_arrow',received:'down_red_arrow',capitalDonated:'capital_gold',gold:'gold',elixir:'elixir',darkElixir:'dark_elixir',warStars:'war_star',warWinRate:'wood_swords',warsWon:'wood_swords',warsSpun:'animated_clash_swords',capitalRaided:'capital_gold',raidParticipants:'people',capitalTrophies:'capital_trophy',cwlLeague:'Master League I',clanMoves:'people'};
