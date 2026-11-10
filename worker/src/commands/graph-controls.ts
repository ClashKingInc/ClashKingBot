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
import { emojis } from "./game-common";
import type { CommandContext } from "./types";

export interface GraphClan {
  tag: string;
  name: string;
  category?: string | null;
}
export interface GraphClans {
  base: GraphClan[];
  choices: GraphClan[];
  selected: GraphClan[];
  // Empty means all; explicit selections are rendered in full, independent of
  // the slash limit used to rank the complete family/category.
  selectedTags: string[];
  categoryKey: string;
}
async function categoryKey(name: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(name));
  return Array.from(new Uint8Array(bytes).slice(0, 8), byte => byte.toString(16).padStart(2, "0")).join("");
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
  const family = await ctx.services.api.get<GraphClan[]>(
    `/v2/server/${requireGuildId(ctx)}/clans-basic`,
  );
  const category = stringOption(ctx, "clan_category");
  const key = stringOption(ctx, "__graph_category") ?? (category ? await categoryKey(category) : "all");
  const categories = [...new Set(family.map(clan => clan.category).filter((name): name is string => !!name))];
  const matching = key === "all" ? undefined : (await Promise.all(categories.map(async name => ({name, key: await categoryKey(name)})))).find(item => item.key === key)?.name;
  if (key !== "all" && !matching)
    throw new CommandInputError("That clan category is no longer available. Run /graph again.");
  const base = [...new Map(family.filter(clan => key === "all" || clan.category === matching).map(clan => [clan.tag, clan])).values()];
  if (!base.length || base.length > 50)
    throw new CommandInputError("Choose a family or category with 1–50 linked clans.");

  // Rank the entire scope before truncating, then alphabetize the 24 choices.
  // Cached member counts avoid one live Clash API request per linked clan.
  const counts = new Map<string, number>();
  let next = 0;
  const deadline = AbortSignal.timeout(15_000);
  await Promise.all(Array.from({length: Math.min(5, base.length)}, async () => {
    while (next < base.length) {
      const clan = base[next++]!;
      const cached = await ctx.services.api.get<{memberCount: number} | null>(
        `/v2/clan/${encodeURIComponent(clan.tag)}/cached`, {}, deadline,
      );
      if (cached && Number.isSafeInteger(cached.memberCount) && cached.memberCount > 0)
        counts.set(clan.tag, cached.memberCount);
    }
  }));
  const alphabetical = (a: GraphClan, b: GraphClan) => a.name.localeCompare(b.name) || a.tag.localeCompare(b.tag);
  const choices = base.filter(clan => counts.has(clan.tag))
    .sort((a, b) => counts.get(b.tag)! - counts.get(a.tag)! || alphabetical(a, b))
    .slice(0, 24).sort(alphabetical);
  const selectedTags = (stringOption(ctx, "__graph_clans") ?? "all").split(",");
  if (!selectedTags.length || selectedTags.length > 24 || new Set(selectedTags).size !== selectedTags.length ||
      selectedTags.some(tag => tag !== "all" && !choices.some(clan => clan.tag === tag)))
    throw new CommandInputError("A selected clan is no longer available. Run /graph again or choose other clans.");
  // All wins when combined with individual options, so the menu always has an
  // unambiguous scope and can return to the complete family/category.
  const tags = selectedTags.includes("all") ? [] : selectedTags;
  return {base, choices, selected: tags.length ? base.filter(clan => tags.includes(clan.tag)) : base,
    selectedTags: tags, categoryKey: key};
}
export function graphScope(clans: GraphClans, shown?: number, order = "desc") {
  if (clans.selected.length === 1) return clans.selected[0]!.name;
  const scope = clans.selectedTags.length ? "selected clans" : clans.categoryKey === "all" ? "family clans" : "category clans";
  return shown && shown < clans.selected.length
    ? `${order === "asc" ? "Bottom" : "Top"} ${shown} of ${clans.selected.length} ${scope}`
    : `${clans.selected.length} ${scope}`;
}
const viewCode = { month: "m", "over-time": "t", daily: "d" } as const;
function id(ctx: CommandContext, state: GraphControlState, clans: GraphClans, action: string) {
  // Selections live in the message's option defaults, not custom_id: 24 tags
  // exceed Discord's 100-character ID limit. Bind every control to its guild.
  return ["ck", "chart", viewCode[state.view], state.metric, state.period,
    state.count, state.limit, state.order, requireGuildId(ctx), clans.categoryKey, action].join(":");
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
      custom_id: id(ctx, state, clans, "metric"),
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
  result.push(actionRow({type:3,custom_id:id(ctx,state,clans,"view"),placeholder:"Chart view",options:[
    ...(Object.hasOwn(dailyMetrics,state.metric)?[{label:"Daily trend",value:"daily",default:state.view==="daily"}]:[]),
    ...(Object.hasOwn(graphMetrics,state.metric)?[...(state.metric!=="cwlLeague"?[{label:"Season totals",value:"month",default:state.view==="month"}]:[]),{label:"Season trend",value:"over-time",default:state.view==="over-time"}]:[]),
  ]}));
  result.push(actionRow({
    type: 3,
    custom_id: id(ctx, state, clans, "clan"),
    placeholder: "Choose 1–24 clans",
    min_values: 1,
    max_values: Math.min(24, clans.choices.length + 1),
    options: [{label: clans.categoryKey === "all" ? "All family clans" : "All category clans", value: "all", default: !clans.selectedTags.length},
      ...clans.choices.map(clan => ({label: clan.name.slice(0, 100), description: clan.tag, value: clan.tag, default: clans.selectedTags.includes(clan.tag)}))],
  }));

  if(state.view==="month"){
    const seasons=Array.from({length:12},(_,index)=>{const date=new Date();date.setUTCDate(1);date.setUTCMonth(date.getUTCMonth()-index);return {label:date.toLocaleDateString("en",{month:"long",year:"numeric",timeZone:"UTC"}),value:date.toISOString().slice(0,7),default:state.period===date.toISOString().slice(0,7)};});
    result.push(actionRow({type:3,custom_id:id(ctx,state,clans,"period"),placeholder:"Season",options:[{label:"Current season",value:"current",default:state.period==="current"},...seasons]}));
  }
  const icon=(await emojis(ctx)).component("refresh");
  const ranges=state.view==="daily"?[7,30,90,180]:state.view==="over-time"?[2,4,6,12]:[];
  result.push(actionRow(...ranges.map(count=>({type:2 as const,style:state.count===count?1 as const:2 as const,label:state.view==="daily"?`${count}d`:`${count} seasons`,custom_id:id(ctx,state,clans,`range${count}`)})),{type:2,style:2,emoji:icon??{name:"↻"},custom_id:id(ctx,state,clans,"refresh")}));
  return result;
}
function selectedClans(ctx: CommandContext, controlId: string): string[] {
  const components = ctx.interaction.message?.components;
  if (Array.isArray(components)) for (const row of components) {
    if (!Array.isArray(row.components)) continue;
    for (const component of row.components) {
      if (component.custom_id === controlId && Array.isArray(component.options)) {
        const selected = (component.options as StringSelectOption[]).filter(option => option.default).map(option => option.value);
        if (selected.length) return selected;
      }
    }
  }
  throw new CommandInputError("Run /graph again to restore its clan selection.");
}
export async function dispatchGraphControl(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const parts = (ctx.interaction.data?.custom_id ?? "").split(":");
  if (parts.length !== 11 || parts[0] !== "ck" || parts[1] !== "chart")
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
    guild,
    category,
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
    guild !== requireGuildId(ctx) || !/^(all|[a-f0-9]{16})$/u.test(category!) ||
    !["metric", "clan", "refresh", "view", "period", "range2", "range4", "range6", "range7", "range12", "range30", "range90", "range180"].includes(
      action!,
    ) ||
    !["asc", "desc"].includes(order!) ||
    !/^\d{1,3}$/u.test(countRaw!) ||
    !/^\d{1,2}$/u.test(limitRaw!) ||
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
  const selected = action === "clan" ? ctx.interaction.data?.values : selectedClans(ctx, [...parts.slice(0, -1), "clan"].join(":"));
  if (!selected?.length || selected.length > 24)
    throw new CommandInputError("Choose 1–24 clans.");
  const selection = selected.includes("all") ? "all" : selected.map(tag => normalizeTag(tag, ctx.locale)).join(",");
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
    { name: "__graph_clans", type: OptionType.String, value: selection },
    { name: "__graph_category", type: OptionType.String, value: category! },
  ];
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
