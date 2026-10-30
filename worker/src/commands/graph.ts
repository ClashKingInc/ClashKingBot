import { graphMetrics, graphTotal, validGraphValue } from "./graph-data";
export { graphMetrics } from "./graph-data";
import { dailyMetrics } from "./graph-data";
import { graphDaily } from "./graph-daily";
import { barChartSvg, chartDate } from "./graph-renderer";
import { graphControls, graphScope, resolveGraphClans } from "./graph-controls";
import { legacyMessage } from "../discord/components";
import { CommandInputError, OptionType, stringOption } from "./command-utils";
import { subcommand } from "./game-common";
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
    name: "graph",
    description: "Charts of recorded clan statistics",
    type: 1,
    options: [
      {
        name: "month",
        description: "Compare clan contribution totals in a game season",
        type: OptionType.Subcommand,
        options: [
          {
            name: "attribute",
            description: "Statistic to compare (default Donations)",
            type: OptionType.String,
            choices: Object.entries(graphMetrics).map(([value, name]) => ({
              name,
              value,
            })),
          },
          {
            name: "season",
            description: "Game season YYYY-MM (default current)",
            type: OptionType.String,
          },
          {
            name: "clans",
            description: "Space-separated clan tags (default linked family)",
            type: OptionType.String,
            max_length: 250,
          },
          {
            name: "limit",
            description: "Top clans to chart (default 10)",
            type: OptionType.Integer,
            min_value: 1,
            max_value: 15,
          },
          {
            name: "sort_order",
            description: "Order by recorded total",
            type: OptionType.String,
            choices: [
              { name: "Descending", value: "desc" },
              { name: "Ascending", value: "asc" },
            ],
          },
        ],
      },
    ],
  },
  async execute(context) {
    const ctx = subcommand(context),
      attribute = stringOption(ctx, "attribute") ?? "donated",
      season = stringOption(ctx, "season") ?? "current",
      limit = Number(ctx.options.get("limit")?.value ?? 10),
      order = stringOption(ctx, "sort_order") ?? "desc";
    if (ctx.path[0] === "daily") return graphDaily(ctx);
    if (
      !Object.hasOwn(graphMetrics, attribute) ||
      (season !== "current" && !/^\d{4}-(0[1-9]|1[0-2])$/u.test(season)) ||
      !Number.isInteger(limit) ||
      limit < 1 ||
      limit > 15 ||
      !["asc", "desc"].includes(order)
    )
      throw new CommandInputError("Choose valid chart options.");
    if (ctx.path[0] === "over-time")
      return (await import("./graph-series")).graphSeries(ctx);
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
    const { posterArtwork, renderPosterSvg } = await import("./legend-poster");
    const svg = barChartSvg({
      title: graphMetrics[attribute as Metric],
      subtitle: `${graphScope(clans, selected.length, order)} · ${chartDate(resolved, true)}`,
      logo: posterArtwork.logo,
      rows: selected,
      note: unavailable ? "Some clan totals are unavailable" : undefined,
    });
    const response = legacyMessage({
      allowed_mentions: { parse: [] },
      components: await graphControls(
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
    });
    response.data!.attachments = [];
    response.data!.__files = [
      { name: "clan-contributions.png", bytes: await renderPosterSvg(svg) },
    ];
    return response;
  },
};

graphCommand.definition.options!.push({
  name: "over-time",
  description: "Compare recorded contributions across game seasons",
  type: OptionType.Subcommand,
  options: [
    {
      name: "attribute",
      description: "Statistic to compare (default Donations)",
      type: OptionType.String,
      choices: Object.entries(graphMetrics).map(([value, name]) => ({
        name,
        value,
      })),
    },
    {
      name: "season",
      description: "Last game season YYYY-MM (default current)",
      type: OptionType.String,
    },
    {
      name: "months",
      description: "Number of game seasons (default 4)",
      type: OptionType.Integer,
      min_value: 2,
      max_value: 12,
    },
    {
      name: "limit",
      description: "Clans ranked by final-season total (default 5)",
      type: OptionType.Integer,
      min_value: 1,
      max_value: 10,
    },
    {
      name: "clans",
      description: "Space-separated clan tags (default linked family)",
      type: OptionType.String,
      max_length: 250,
    },
  ],
});

graphCommand.definition.options!.push({
  name: "daily",
  description: "Daily observations and gains for clans or a family",
  type: OptionType.Subcommand,
  options: [
    {
      name: "attribute",
      description: "Statistic to graph (default Activity)",
      type: OptionType.String,
      choices: Object.entries(dailyMetrics).map(([value, name]) => ({
        name,
        value,
      })),
    },
    {
      name: "days",
      description: "UTC days to show, including today (default 30)",
      type: OptionType.Integer,
      min_value: 1,
      max_value: 180,
    },
    {
      name: "limit",
      description: "Clans ranked by window total (default 5)",
      type: OptionType.Integer,
      min_value: 1,
      max_value: 10,
    },
    {
      name: "clans",
      description: "Space-separated clan tags (default linked family)",
      type: OptionType.String,
      max_length: 250,
    },
  ],
});
