import { graphMetrics, graphTotal, validGraphValue } from "./graph-data";
export { graphMetrics } from "./graph-data";
import { dailyMetrics } from "./graph-data";
import { graphDaily } from "./graph-daily";
import { barChartSvg, chartDate } from "./graph-renderer";
import { graphControls, graphScope, resolveGraphClans } from "./graph-controls";
import { componentsV2 } from "../discord/components";
import { CommandInputError, OptionType, stringOption } from "./command-utils";
import type { Command } from "./types";

type Metric = keyof typeof graphMetrics;
interface Row {
  tag: string;
  name: string;
  value: number | null;
}
export const graphCommand: Command = {
  deferred: true,
  definition: {
    name:"graph",description:"Explore clan and family statistics",type:1,
    options:[
      {name:"attribute",description:"Statistic (default Activity)",type:OptionType.String,choices:Object.entries({...graphMetrics,...dailyMetrics}).map(([value,name])=>({name,value}))},
      {name:"clans",description:"Clan tags (default linked family)",type:OptionType.String,max_length:250},
      {name:"limit",description:"Clans to compare (default 5)",type:OptionType.Integer,min_value:1,max_value:5},
    ],
  },
  async execute(context) {
    const ctx = context,
      attribute = stringOption(ctx, "attribute") ?? "activity",
      season = stringOption(ctx, "season") ?? "current",
      limit = Number(ctx.options.get("limit")?.value ?? 5),
      order = stringOption(ctx, "sort_order") ?? "desc";
    const view=attribute==="cwlLeague"?"over-time":stringOption(ctx,"__view")??(Object.hasOwn(dailyMetrics,attribute)?"daily":"month");
    if(view==="daily")return graphDaily(ctx);

    if (
      !Object.hasOwn(graphMetrics, attribute) ||
      (season !== "current" && !/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)) ||
      !Number.isInteger(limit) ||
      limit < 1 ||
      limit > 5 ||
      !["asc", "desc"].includes(order)
    )
      throw new CommandInputError("Choose valid chart options.");
    if (view === "over-time")
      return (await import("./graph-series")).graphSeries(ctx);
    if(view!=="month")throw new CommandInputError("Choose a chart view.");
    const clans = await resolveGraphClans(ctx),
      refs = clans.selected;
    const rows: Row[] = [];
    let resolved = season,
      unavailable = 0;
    for (let i = 0; i < refs.length; i += 5) {
      const batch = refs.slice(i, i + 5),
        results = await Promise.allSettled(
          batch.map((ref) =>
            graphTotal(ctx, ref.tag, season, attribute as Metric),
          ),
        );
      for (const [j, result] of results.entries()) {
        const ref = batch[j]!;
        if (result.status === "rejected" || result.value.value === null) {
          unavailable++;
          rows.push({ ...ref, value: null });
          continue;
        }
        if (resolved !== "current" && resolved !== result.value.season)
          throw new CommandInputError(
            "The season changed during this chart. Refresh it.",
          );
        resolved = result.value.season;
        const sum = result.value.value;
        if (!validGraphValue(attribute, sum)) {
          unavailable++;
          rows.push({ ...ref, value: null });
          continue;
        }
        rows.push({ ...ref, value: sum });
      }
    }
    const selected = rows
      .filter((row): row is Row & { value: number } => row.value !== null)
      .sort(
        (a, b) =>
          (order === "desc" ? -1 : 1) * (a.value - b.value) ||
          a.tag.localeCompare(b.tag),
      )
      .slice(0, limit);
    const { posterArtwork } = await import("./legend-poster");
  const { renderGraphSvg, graphDecoration } = await import("./graph-image");
  const decoration=await graphDecoration(ctx,attribute,selected);
    const svg = barChartSvg({
      title: graphMetrics[attribute as Metric],
      subtitle: `${graphScope(clans, selected.length, order)} | ${chartDate(resolved, true)}`,
      logo: posterArtwork.logo,
    icon: decoration.icon,
    valueSuffix: attribute === "warWinRate" ? "%" : undefined,
      rows: decoration.rows,
      note: unavailable ? "Some clan totals are unavailable" : undefined,
    });
    const response = componentsV2([{type:12,items:[{media:{url:"attachment://clan-contributions.png"}}]},...await graphControls(
        ctx,
        {
          view: "month",
          metric: attribute,
          period: season,
          count: 1,
          limit,
          order,
        },
        clans,
      ),
    ]);
    response.data!.attachments = [];
    response.data!.__files = [
      { name: "clan-contributions.png", bytes: await renderGraphSvg(svg) },
    ];
    return response;
  },
};
