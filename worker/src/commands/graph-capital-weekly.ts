import { legacyMessage } from "../discord/components";
import { CommandInputError } from "./command-utils";
import type { CommandContext } from "./types";
import { lineChartSvg, chartDate } from "./graph-renderer";
import { graphControls, graphScope, type GraphClans } from "./graph-controls";
interface History {
  weeks: string[];
  values: Array<number | null>;
  sampleDates: Array<string | null>;
}
export async function graphCapitalWeekly(
  ctx: CommandContext,
  clans: GraphClans,
  season: string,
  months: number,
  limit: number,
) {
  const refs = clans.selected;
  const rows: Array<History & { tag: string; name: string }> = [];
  let failed = 0;
  let weeks: string[] = [];
  const deadline = AbortSignal.timeout(25000);
  for (let i = 0; i < refs.length && !deadline.aborted; i += 5) {
    const result = await Promise.allSettled(
      refs.slice(i, i + 5).map(async (ref) => ({
        ...ref,
        ...(await ctx.services.api.get<History>(
          `/v2/bot/clans/${encodeURIComponent(ref.tag)}/capital-trophy-history`,
          { months, ...(season === "current" ? {} : { season }) },
          deadline,
        )),
      })),
    );
    for (const value of result) {
      if (value.status === "rejected") {
        failed++;
        continue;
      }
      const row = value.value;
      if (
        !row.weeks.length ||
        row.weeks.length !== row.values.length ||
        row.sampleDates.length !== row.values.length ||
        row.values.some(
          (n) => n !== null && (!Number.isSafeInteger(n) || n < 0),
        )
      )
        throw new CommandInputError("Capital history could not be validated.");
      if (!weeks.length) weeks = row.weeks;
      else if (JSON.stringify(weeks) !== JSON.stringify(row.weeks))
        throw new CommandInputError(
          "The history window changed. Refresh the chart.",
        );
      rows.push(row);
    }
  }
  failed = refs.length - rows.length;
  if (!weeks.length)
    throw new CommandInputError(
      "Capital trophy history is unavailable. Try again later.",
    );
  const latest = (values: Array<number | null>) =>
    values.findLast((value): value is number => value !== null) ?? -1;
  const selected = rows
    .filter((row) => latest(row.values) >= 0)
    .sort(
      (a, b) =>
        latest(b.values) - latest(a.values) || a.tag.localeCompare(b.tag),
    )
    .slice(0, limit);
  const { posterArtwork, renderPosterSvg } = await import("./legend-poster");
  const missing =
    failed > 0 ||
    selected.some((row) => row.values.some((value) => value === null));
  const svg = lineChartSvg({
    title: "Capital trophies",
    subtitle: `${graphScope(clans, selected.length)} · ${chartDate(weeks[0]!)} – ${chartDate(weeks.at(-1)!)}`,
    logo: posterArtwork.logo,
    labels: weeks.map((week) => chartDate(week)),
    series: selected,
    note: missing
      ? "Weekly snapshots · missing periods are left as gaps"
      : "Weekly snapshots · this week is still in progress",
  });
  const response = legacyMessage({
    allowed_mentions: { parse: [] },
    components: await graphControls(
      ctx,
      {
        view: "over-time",
        metric: "capitalTrophies",
        period: season,
        count: months,
        limit,
        order: "desc",
      },
      clans,
    ),
  });
  response.data!.attachments = [];
  response.data!.__files = [
    { name: "capital-trophy-history.png", bytes: await renderPosterSvg(svg) },
  ];
  return response;
}
