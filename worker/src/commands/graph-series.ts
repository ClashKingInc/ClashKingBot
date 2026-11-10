import { componentsV2 } from "../discord/components";
import { CommandInputError, stringOption } from "./command-utils";
import { graphMetrics, graphTotal, validGraphValue } from "./graph-data";
import type { CommandContext } from "./types";
import { lineChartSvg, chartDate } from "./graph-renderer";
import { graphControls, graphScope, resolveGraphClans } from "./graph-controls";
type Metric = keyof typeof graphMetrics;
interface Stats {
  season: string;
  truncated: boolean;
  items: Array<Record<Metric, number>>;
}
export async function graphSeries(ctx: CommandContext) {
  const metric = (stringOption(ctx, "attribute") ?? "donated") as Metric,
    requested = stringOption(ctx, "season") ?? "current",
    count = Number(ctx.options.get("months")?.value ?? 4),
    limit = Number(ctx.options.get("limit")?.value ?? 5);
  if (
    !Object.hasOwn(graphMetrics, metric) ||
    !Number.isInteger(count) ||
    count < 2 ||
    count > 12 ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 5
  )
    throw new CommandInputError("Choose 2–12 seasons and 1–5 clans.");
  const clans = await resolveGraphClans(ctx),
    refs = clans.selected;
  if(metric === "cwlLeague") return (await import("./graph-cwl")).graphCwl(ctx,clans,requested,count,limit);
  let season = requested;
  if (season === "current") {
    try {
      season = (
        await Promise.any(
          refs
            .slice(0, 5)
            .map((ref) =>
              ctx.services.api.get<Stats>(
                `/v2/bot/clans/${encodeURIComponent(ref.tag)}/season-stats`,
                {},
                AbortSignal.timeout(8000),
              ),
            ),
        )
      ).season;
    } catch {
      throw new CommandInputError(
        "Could not resolve the current game season. Try again.",
      );
    }
  }
  const end = new Date(`${season}-01T00:00:00Z`);
  if (!Number.isFinite(+end) || end.toISOString().slice(0, 7) !== season)
    throw new CommandInputError("Choose a season in YYYY-MM format.");
  const seasons = Array.from({ length: count }, (_, i) =>
    new Date(
      Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - count + i + 1, 1),
    )
      .toISOString()
      .slice(0, 7),
  );
  const rows = refs.map((ref) => ({
    ...ref,
    values: Array.from<number | null>({ length: count }).fill(null),
  }));
  const jobs = rows.flatMap((row) =>
    seasons.map((value, index) => ({ row, value, index })),
  );
  let next = 0,
    missing = jobs.length;
  const deadline = AbortSignal.timeout(25_000);
  // Missing/truncated requests stay null. Do not connect a line through a gap
  // or treat an unfinished request as a season with zero recorded contributions.
  await Promise.all(
    Array.from({ length: Math.min(5, jobs.length) }, async () => {
      while (next < jobs.length && !deadline.aborted) {
        const job = jobs[next++]!;
        try {
          const data = await graphTotal(
            ctx,
            job.row.tag,
            job.value,
            metric,
            deadline,
          );
          const sum = data.value;
          if (
            data.season === job.value &&
            sum !== null &&
            validGraphValue(metric, sum)
          ) {
            job.row.values[job.index] = sum;
            missing--;
          }
        } catch {
          /* The chart marks this observation unavailable. */
        }
      }
    }),
  );
  const selected = rows
    .filter((row) => row.values[count - 1] !== null)
    .sort(
      (a, b) =>
        b.values[count - 1]! - a.values[count - 1]! ||
        a.tag.localeCompare(b.tag),
    )
    .slice(0, clans.selectedTags.length || limit);
  const { posterArtwork } = await import("./legend-poster");
  const { renderGraphSvg, graphDecoration } = await import("./graph-image");
  const decoration=await graphDecoration(ctx,metric,selected);
  const svg = lineChartSvg({
    title: graphMetrics[metric],
    subtitle: `${graphScope(clans, selected.length)} | ${chartDate(seasons[0]!, true)} – ${chartDate(season, true)}`,
    logo: posterArtwork.logo,
    icon: decoration.icon,
    valueSuffix: metric === "warWinRate" ? "%" : undefined,
    labels: seasons.map((value) => chartDate(value, true)),
    series: decoration.rows.map((row) => ({ name: row.name, values: row.values,
      ...(!["raidParticipants","warWinRate","capitalTrophies","cwlLeague"].includes(metric)?{headline:row.values.some(v=>v!==null)?row.values.reduce<number>((sum,value)=>sum+(value??0),0):null}:{}),
    })),
    note: missing ? "Some periods unavailable" : undefined,
  });
  const response = componentsV2([{type:12,items:[{media:{url:"attachment://clan-contributions.png"}}]},...await graphControls(
      ctx,
      {
        view: "over-time",
        metric,
        period: requested,
        count,
        limit,
        order: "desc",
      },
      clans,
    ),
  ]);
  response.data!.attachments = [];
  response.data!.__files = [
    { name: "clan-contributions.png", bytes: await renderGraphSvg(svg) },
  ];
  return response;
}
