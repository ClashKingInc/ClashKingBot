import { sendInteractionError } from "./errors";
import {
  actionRow,
  type ActionRowComponent,
  type StringSelectOption,
} from "../discord/components";
import {
  InteractionResponseType,
  type DiscordInteractionResponse,
  type InteractionOption,
} from "../discord/types";
import {
  CommandInputError,
  normalizeTag,
  OptionType,
  requireGuildId,
  stringOption,
} from "./command-utils";
import { dailyMetrics, graphMetrics, graphMetricIcons } from "./graph-data";
import { clanSelector } from "./clan-selector";
import { emojis } from "./game-common";
import type { CommandContext } from "./types";

export interface GraphClan {
  tag: string;
  name: string;
}
export interface GraphClans {
  base: GraphClan[];
  selected: GraphClan[];
  custom: boolean;
  selectedTag: string;
  page: number;
}
export interface GraphControlState {
  view: "month" | "over-time" | "daily";
  metric: string;
  period: string;
  count: number;
  limit: number;
  order: string;
}
export async function resolveGraphClans(
  ctx: CommandContext,
): Promise<GraphClans> {
  const raw = stringOption(ctx, "clans") ?? "";
  const base = raw
    ? [
        ...new Set(
          raw
            .split(/[\s,]+/u)
            .filter(Boolean)
            .map((tag) => normalizeTag(tag, ctx.locale)),
        ),
      ].map((tag) => ({ tag, name: tag }))
    : await ctx.services.api.get<GraphClan[]>(
        `/v2/server/${requireGuildId(ctx)}/clans-basic`,
      );
  if (!base.length || base.length > 50)
    throw new CommandInputError(
      "Choose 1–50 clans or link a family on the dashboard.",
    );
  const selectedTag = stringOption(ctx, "__graph_clan") ?? "all";
  if (selectedTag !== "all" && !base.some((clan) => clan.tag === selectedTag))
    throw new CommandInputError(
      "That clan is no longer available in this chart.",
    );
  const page = Number(ctx.options.get("__graph_clan_page")?.value ?? 0);
  if (!Number.isInteger(page) || page < 0 || page > 100)
    throw new CommandInputError("Invalid clan page.");
  return {
    base,
    selected:
      selectedTag === "all"
        ? base
        : base.filter((clan) => clan.tag === selectedTag),
    custom: !!raw,
    selectedTag,
    page,
  };
}
export function graphScope(clans: GraphClans, shown?: number, order = "desc") {
  if (clans.selected.length === 1) return clans.selected[0]!.name;
  const scope = clans.custom ? "selected clans" : "family clans";
  return shown && shown < clans.selected.length
    ? `${order === "asc" ? "Bottom" : "Top"} ${shown} of ${clans.selected.length} ${scope}`
    : `${clans.selected.length} ${scope}`;
}
const viewCode = { month: "m", "over-time": "t", daily: "d" } as const;
function id(state: GraphControlState, clans: GraphClans, action: string) {
  return [
    "ck",
    "chart",
    viewCode[state.view],
    state.metric,
    state.period,
    state.count,
    state.limit,
    state.order,
    clans.selectedTag === "all" ? "all" : clans.selectedTag.slice(1),
    clans.page,
    clans.custom ? "c" : "f",
    action,
  ].join(":");
}
export async function graphControls(
  ctx: CommandContext,
  state: GraphControlState,
  clans: GraphClans,
): Promise<ActionRowComponent[]> {
  const metrics = {...graphMetrics,...dailyMetrics},art=await emojis(ctx);
  const result = [
    actionRow({
      type: 3,
      custom_id: id(state, clans, "metric"),
      placeholder: "Statistic",
      min_values: 1,
      max_values: 1,
      options: Object.entries(metrics).map(([value, label]) => ({
        label,
        value,
        default: value === state.metric,
        ...(art.component(graphMetricIcons[value]??"")?{emoji:art.component(graphMetricIcons[value]??"")}:{}) ,
      })),
    }),
  ];
  result.push(actionRow({type:3,custom_id:id(state,clans,"view"),placeholder:"Chart view",options:[
    ...(Object.hasOwn(dailyMetrics,state.metric)?[{label:"Daily trend",value:"daily",default:state.view==="daily"}]:[]),
    ...(Object.hasOwn(graphMetrics,state.metric)?[...(state.metric!=="cwlLeague"?[{label:"Season totals",value:"month",default:state.view==="month"}]:[]),{label:"Season trend",value:"over-time",default:state.view==="over-time"}]:[]),
  ]}));
  const all = {
    label: clans.custom ? "All selected clans" : "All family clans",
    value: "all" as const,
    default: clans.selectedTag === "all",
  };
  if (clans.custom) {
    // Keep explicit clan choices in the message itself. This preserves the
    // exact custom scope across metric switches without opaque server state.
    // Components V2 lets up to 50 custom clans occupy three selector rows.
    for (let index = 0; index < clans.base.length; index += 24) {
      const options: StringSelectOption[] = clans.base
        .slice(index, index + 24)
        .map((clan) => ({
          label: clan.name.slice(0, 100),
          value: clan.tag,
          default: clans.selectedTag === clan.tag,
        }));
      if (index === 0) options.unshift(all);
      result.push(
        actionRow({
          type: 3,
          custom_id: id(state, clans, `clan${index / 24}`),
          placeholder:
            clans.base.length > 24
              ? `Clans ${index + 1}–${Math.min(index + 24, clans.base.length)}`
              : "Clan",
          min_values: 1,
          max_values: 1,
          options,
        }),
      );
    }
  } else {
    result.push(
      clanSelector({
        clans: clans.base,
        selectedTag: clans.selectedTag,
        page: clans.page,
        customId: id(state, clans, "clan"),
        includeAll: all,
      }).row,
    );
  }

  if(state.view==="month"){
    const seasons=Array.from({length:12},(_,index)=>{const date=new Date();date.setUTCDate(1);date.setUTCMonth(date.getUTCMonth()-index);return {label:date.toLocaleDateString("en",{month:"long",year:"numeric",timeZone:"UTC"}),value:date.toISOString().slice(0,7),default:state.period===date.toISOString().slice(0,7)};});
    result.push(actionRow({type:3,custom_id:id(state,clans,"period"),placeholder:"Season",options:[{label:"Current season",value:"current",default:state.period==="current"},...seasons]}));
  }
  const icon=(await emojis(ctx)).component("refresh");
  const ranges=state.view==="daily"?[7,30,90,180]:state.view==="over-time"?[2,4,6,12]:[];
  result.push(actionRow(...ranges.map(count=>({type:2 as const,style:state.count===count?1 as const:2 as const,label:state.view==="daily"?`${count}d`:`${count} seasons`,custom_id:id(state,clans,`range${count}`)})),{type:2,style:2,emoji:icon??{name:"↻"},custom_id:id(state,clans,"refresh")}));
  return result;
}
function customClans(ctx: CommandContext): string {
  const components = ctx.interaction.message?.components;
  if (!Array.isArray(components))
    throw new CommandInputError(
      "Run the chart command again to restore its selected clans.",
    );
  const tags = new Set<string>();
  for (const row of components) {
    if (!row || typeof row !== "object" || !Array.isArray(row.components))
      continue;
    for (const component of row.components) {
      if (
        !component ||
        typeof component !== "object" ||
        typeof component.custom_id !== "string" ||
        !component.custom_id.startsWith("ck:chart:") ||
        !/:clan[0-2]?$/u.test(component.custom_id) ||
        !Array.isArray(component.options)
      )
        continue;
      for (const option of component.options)
        if (typeof option?.value === "string" && option.value.startsWith("#"))
          tags.add(normalizeTag(option.value, ctx.locale));
    }
  }
  if (!tags.size || tags.size > 50)
    throw new CommandInputError(
      "Run the chart command again to restore its selected clans.",
    );
  return [...tags].join(" ");
}
export async function dispatchGraphControl(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const parts = (ctx.interaction.data?.custom_id ?? "").split(":");
  if (parts.length !== 12 || parts[0] !== "ck" || parts[1] !== "chart")
    throw new CommandInputError("Invalid chart control.");
  const [
    ,
    ,
    code,
    oldMetric,
    period,
    countRaw,
    limitRaw,
    order,
    clan,
    pageRaw,
    source,
    action,
  ] = parts;
  let view =
    code === "m"
      ? "month"
      : code === "t"
        ? "over-time"
        : code === "d"
          ? "daily"
          : undefined;
  if (
    !view ||
    !["c", "f"].includes(source!) ||
    !["metric", "clan", "clan0", "clan1", "clan2", "refresh", "view", "period", "range2", "range4", "range6", "range7", "range12", "range30", "range90", "range180"].includes(
      action!,
    ) ||
    !["asc", "desc"].includes(order!) ||
    !/^\d{1,3}$/u.test(countRaw!) ||
    !/^\d{1,2}$/u.test(limitRaw!) ||
    !/^\d{1,3}$/u.test(pageRaw!) ||
    (period !== "current" && !/^\d{4}-(0[1-9]|1[0-2])$/u.test(period!))
  )
    throw new CommandInputError("Invalid chart control.");
  const value = ctx.interaction.data?.values?.[0];
  const metric=action==="metric"?value:oldMetric,metrics={...graphMetrics,...dailyMetrics};
  if(!metric||!Object.hasOwn(metrics,metric))throw new CommandInputError("Choose a valid statistic.");
  let count=Number(countRaw),selectedPeriod=period!;
  if(action==="view"){
    if(!["daily","month","over-time"].includes(value??""))throw new CommandInputError("Choose a chart view.");
    view=value as typeof view;count=view==="daily"?30:view==="over-time"?4:1;
    if(view==="over-time")selectedPeriod="current";
  }
  if(view==="daily"&&!Object.hasOwn(dailyMetrics,metric)){view="month";count=1;}
  if(view!=="daily"&&!Object.hasOwn(graphMetrics,metric)){view="daily";count=30;}
  if(action==="period"){
    if(!value||value!=="current"&&!/^\d{4}-(0[1-9]|1[0-2])$/u.test(value))throw new CommandInputError("Choose a season.");
    selectedPeriod=value;
  }
  if(action?.startsWith("range")){
    count=Number(action.slice(5));
    if(!(view==="daily"?[7,30,90,180]:view==="over-time"?[2,4,6,12]:[]).includes(count))throw new CommandInputError("Choose a valid period.");
  }
  if(metric==="cwlLeague"&&view!=="over-time"){view="over-time";count=4;}
  let selected = clan === "all" ? "all" : normalizeTag(clan!, ctx.locale),
    page = Number(pageRaw);
  if (action?.startsWith("clan")) {
    if (!value) throw new CommandInputError("Choose a clan.");
    if (/^page:\d{1,3}$/u.test(value)) page = Number(value.slice(5));
    else selected = value === "all" ? "all" : normalizeTag(value, ctx.locale);
  }
  const options: InteractionOption[] = [
    { name: "attribute", type: OptionType.String, value: metric },
    { name: "season", type: OptionType.String, value: selectedPeriod },
    { name: "limit", type: OptionType.Integer, value: Number(limitRaw) },
    { name: "sort_order", type: OptionType.String, value: order! },
    {
      name: view === "daily" ? "days" : "months",
      type: OptionType.Integer,
      value: count,
    },
    { name: "__graph_clan", type: OptionType.String, value: selected },
    { name: "__graph_clan_page", type: OptionType.Integer, value: page },
  ];
  if (source === "c")
    options.push({
      name: "clans",
      type: OptionType.String,
      value: customClans(ctx),
    });
  const context: CommandContext = {
    ...ctx,
    options: new Map([...options,{name:"__view",type:OptionType.String,value:view}].map(option=>[option.name,option])),
  };
  const run = async () =>
    (await import("./graph")).graphCommand.execute(context);
  if (!waitUntil)
    return { ...(await run()), type: InteractionResponseType.UpdateMessage };
  waitUntil(
    run()
      .then((response) =>
        ctx.services.discordRest.editOriginalInteractionResponse(
          ctx.interaction.token,
          response.data ?? {},
        ),
      )
      .catch((error) =>
        sendInteractionError(ctx,error),
      ),
  );
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
