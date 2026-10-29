import { legacyMessage } from "../discord/components";
import { CommandInputError, stringOption } from "./command-utils";
import type { CommandContext } from "./types";
import { dailyMetrics } from "./graph-data";
export { dailyMetrics } from "./graph-data";
import { lineChartSvg, chartDate } from "./graph-renderer";
import { graphControls, graphScope, resolveGraphClans } from "./graph-controls";
interface Data {
  metric: string;
  basis: "recorded_clan" | "latest_stored_members";
  dates: string[];
  series: Array<{ tag: string; values: number[] }>;
}
export async function graphDaily(ctx: CommandContext) {
  const metric = stringOption(ctx, "attribute") ?? "activity",
    days = Number(ctx.options.get("days")?.value ?? 30),
    limit = Number(ctx.options.get("limit")?.value ?? 5);
  if (
    !Object.hasOwn(dailyMetrics, metric) ||
    !Number.isInteger(days) ||
    days < 1 ||
    days > 180 ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 10
  )
    throw new CommandInputError("Choose a metric, 1–180 days and 1–10 clans.");
  const clans = await resolveGraphClans(ctx),
    refs = clans.selected;
  let data: Data;
  try {
    data = await ctx.services.api.post<Data>("/v2/bot/clans/daily-stats", {
      clans: refs.map((ref) => ref.tag),
      metric,
      days,
    });
  } catch {
    throw new CommandInputError(
      "Daily observations are unavailable. Try again later.",
    );
  }
  if (
    data.dates.length !== days ||
    data.series.some(
      (row) =>
        row.values.length !== days ||
        row.values.some((value) => !Number.isSafeInteger(value) || value < 0),
    )
  )
    throw new CommandInputError("Daily observations could not be validated.");
  const names = new Map(refs.map((ref) => [ref.tag, ref.name]));
  const rows = data.series
    .map((row) => ({
      ...row,
      name: names.get(row.tag) ?? row.tag,
      total: row.values.reduce((sum, value) => sum + value, 0),
    }))
    .sort((a, b) => b.total - a.total || a.tag.localeCompare(b.tag))
    .slice(0, limit);
  if (rows.some((row) => !Number.isSafeInteger(row.total)))
    throw new CommandInputError(
      "The daily total exceeds the supported numeric range.",
    );
  const { posterArtwork, renderPosterSvg } = await import("./legend-poster");
  const svg = lineChartSvg({
    title: dailyMetrics[metric as keyof typeof dailyMetrics],
    subtitle: `${graphScope(clans, rows.length)} · ${chartDate(data.dates[0]!)} – ${chartDate(data.dates.at(-1)!)}`,
    logo: posterArtwork.logo,
    labels: data.dates.map((date) => chartDate(date)),
    series: rows,
    note: "Today is still in progress",
  });
  const response = legacyMessage({
    allowed_mentions: { parse: [] },
    components: await graphControls(
      ctx,
      {
        view: "daily",
        metric,
        period: "current",
        count: days,
        limit,
        order: "desc",
      },
      clans,
    ),
  });
  response.data!.attachments = [];
  response.data!.__files = [
    { name: "daily-clan-statistics.png", bytes: await renderPosterSvg(svg) },
  ];
  return response;
}
