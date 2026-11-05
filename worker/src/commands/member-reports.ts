import { sendInteractionError } from "./errors";
import { builderLeagues } from "./builder-leagues";
import { displayNameColumn } from "./display-width";
import { withClanSelector } from "./clan-controls";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType } from "../discord/types";
import {
  CommandInputError,
  OptionType,
  normalizeTag,
  requireGuildId,
  stringOption,
} from "./command-utils";
import { emojis } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { ApplicationCommandOption, CommandContext } from "./types";

type Scope = "clan" | "family";
interface Member {
  tag: string;
  name: string;
  townHallLevel?: number;
  role?: string;
  trophies?: number;
  builderBaseTrophies?: number;
  versusTrophies?: number;
  expLevel?: number;
  donations?: number;
  donationsReceived?: number;
  warStars?: number;
  attackWins?: number;
  defenseWins?: number;
  clanCapitalContributions?: number;
  leagueTier?: { id: number; name: string };
  league?: { name: string };
  heroes?: Array<{ level: number }>;
  clan?: { tag: string };
}
interface Clan {
  tag: string;
  name: string;
  memberList: Member[];
  badgeUrls?: { small?: string };
}
const metrics: Record<
  string,
  { label: string; key: keyof Member; full?: boolean; icon?: string; text?: boolean }
> = {
  townhall: { label: "Town Hall", key: "townHallLevel" },
  name: { label: "Name", key: "name", text: true },
  tag: { label: "Player tag", key: "tag", text: true },
  role: { label: "Clan role", key: "role", text: true },
  league_trophies: { label: "League & Trophies", key: "trophies" },
  builder_trophies: {
    label: "Builder Base Trophies",
    key: "builderBaseTrophies",
  },
  experience: { label: "Experience level", key: "expLevel" },
  war_stars: { label: "War stars", key: "warStars", full: true },
  capital: {
    label: "Capital contributions",
    key: "clanCapitalContributions",
    full: true,
  },
  heroes: { label: "Total hero levels", key: "heroes", full: true },
};
const groups = {
  townhall: "Town Hall",
  role: "Clan role",
  league: "Ranked league",
  location: "Ranking location",
};
export function memberReportOptions(
  action: "compo" | "sorted",
): ApplicationCommandOption[] {
  return action==="sorted"?[{name:"limit",description:"Players to show (default 50)",type:OptionType.Integer,min_value:1,max_value:50}]:[];
}
export async function memberReport(ctx: CommandContext, scope: Scope) {
  const action = ctx.path[0],
    metric =
      stringOption(ctx, action === "compo" ? "type" : "sort_by") ?? "townhall",
    hall = 0,
    limit = action==="sorted"?Number(ctx.options.get("limit")?.value??50):50,
    order = metrics[metric]?.text ? "asc" : "desc";
  if (
    !["compo", "sorted"].includes(action ?? "") ||
    !(action === "compo" ? metric in groups && !(scope === "clan" && metric === "location") : metric in metrics) ||
    !Number.isInteger(hall) ||
    hall < 0 ||
    hall > 30 ||
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 50 ||
    !["asc", "desc"].includes(order)
  )
    throw new CommandInputError("Choose valid member report options.");
  const target =
    scope === "clan"
      ? normalizeTag(stringOption(ctx, "clan") ?? "", ctx.locale)
      : requireGuildId(ctx);
  const refs =
    scope === "clan"
      ? [{ tag: target }]
      : await ctx.services.api.get<Array<{ tag: string }>>(
          `/v2/server/${target}/clans-basic`,
        );
  if (!refs.length) throw new CommandInputError("No family clans are linked to this server.");
  if (refs.length > 200)
    throw new CommandInputError("This report supports up to 200 linked clans.");
  const clans: Clan[] = [];
  let failedClans = 0,
    failedPlayers = 0;
  for (let i = 0; i < refs.length; i += 5) {
    const results = await Promise.allSettled(
      refs
        .slice(i, i + 5)
        .map((clan) =>
          ctx.services.api.get<Clan>(
            `/v2/bot/clash/clans/${encodeURIComponent(clan.tag)}`,
          ),
        ),
    );
    for (const result of results) {
      if (result.status === "fulfilled") clans.push(result.value);
      else failedClans++;
    }
  }
  const unique = new Map<string, Member>();
  for (const clan of clans)
    for (const member of clan.memberList) unique.set(member.tag, member);
  let members = [...unique.values()];
  if (action === "sorted" && metrics[metric]?.full) {
    const loaded: Member[] = [];
    for (let i = 0; i < members.length; i += 5) {
      const results = await Promise.allSettled(
        members
          .slice(i, i + 5)
          .map((member) =>
            ctx.services.api.get<Member>(
              `/v2/bot/clash/players/${encodeURIComponent(member.tag)}`,
            ),
          ),
      );
      for (const result of results) {
        if (result.status === "fulfilled") loaded.push(result.value);
        else failedPlayers++;
      }
    }
    members = loaded;
  }
  members = members.filter((member) => !hall || member.townHallLevel === hall);
  const emoji = await emojis(ctx),
    color = await serverEmbedColor(ctx);
  let rows: string[], label: string;
  if (action === "compo") {
    const countries = new Map<string, string>();
    if (metric === "location")
      for (let i = 0; i < members.length; i += 100) {
        const result = await ctx.services.api.post<{
          items: Array<{ tag: string; location?: { name: string } }>;
        }>("/v2/legends/ranks", {
          tags: members.slice(i, i + 100).map((member) => member.tag),
        });
        for (const item of result.items)
          if (item.location?.name) countries.set(item.tag, item.location.name);
      }
    const buckets = new Map<string, number>();
    for (const member of members) {
      let key: string;
      if (metric === "townhall")
        key = String(member.townHallLevel ?? "Unknown");
      // The official API calls Elders "admin"; keep that wire value out of the UI.
      else if (metric === "role") key = ({ leader: "Leader", coLeader: "Co-Leader", admin: "Elder", elder: "Elder", member: "Member" } as Record<string,string>)[member.role ?? ""] ?? "Unknown";
      else if (metric === "league")
        key = member.leagueTier?.name ?? member.league?.name ?? "Unranked";
      else key = countries.get(member.tag) ?? "Unknown";
      buckets.set(key, (buckets.get(key) ?? 0) + 1);
    }
    rows = [...buckets]
      .sort((a, b) => {
        if (metric === "role") {
          const hierarchy = ["Leader", "Co-Leader", "Elder", "Member", "Unknown"];
          return hierarchy.indexOf(a[0]) - hierarchy.indexOf(b[0]);
        }
        const cmp = metric === "townhall"
          ? Number(a[0]) - Number(b[0])
          : a[1] - b[1];
        return (order === "asc" ? cmp : -cmp) || a[0].localeCompare(b[0]);
      })
      .map(([key, count]) => {
        const name = metric === "townhall" && key !== "Unknown"
          ? `TH${key}`
          : metric === "league" ? key.replace(/\s+League\b/giu, "") : key;
        const icon = metric === "townhall" && key !== "Unknown" ? emoji.get(Number(key)) : metric === "league" ? emoji.get(key) : "";
        const share = `${members.length ? ((count / members.length) * 100).toFixed(1) : "0.0"}%`;
        // Keep variable-width game icons outside the fixed-width data columns.
        return `${icon ? `${icon} ` : ""}\`${displayNameColumn(name, metric === "location" ? 20 : 13)} ${String(count).padStart(3)} ${share.padStart(6)}\``;
      });
    label = groups[metric as keyof typeof groups];
  } else {
    const rule = metrics[metric]!;
    label = rule.label;
    const value = (member: Member) =>
      metric === "heroes"
        ? member.heroes?.reduce((sum, hero) => sum + hero.level, 0)
        : metric === "builder_trophies"
          ? (member.builderBaseTrophies ?? member.versusTrophies)
          : member[rule.key];
    const measured = members.flatMap((member) => {
      const raw = value(member);
      const measuredValue = metric === "role"
        ? ({ leader:"Leader",coLeader:"Co-Leader",admin:"Elder",elder:"Elder",member:"Member" } as Record<string,string>)[String(raw)] ?? "Unknown"
        : raw;
      return typeof measuredValue === "string" || typeof measuredValue === "number" && Number.isFinite(measuredValue)
        ? [{ member, value: measuredValue }]
        : [];
    });
    failedPlayers += members.length - measured.length;
    measured.sort((a,b)=>{
      // Ranked trophies reset between tiers, so compare the tier before its trophies.
      if (metric === "league_trophies") {
        const tierDifference=(b.member.leagueTier?.id??0)-(a.member.leagueTier?.id??0);
        if(tierDifference)return tierDifference;
      }
      const difference = typeof a.value === "number" && typeof b.value === "number"
        ? b.value-a.value : String(a.value).localeCompare(String(b.value));
      return difference || a.member.name.localeCompare(b.member.name) || a.member.tag.localeCompare(b.member.tag);
    });
    const builderTiers=metric==="builder_trophies"?await builderLeagues():[];
    const format=(value:string|number)=>typeof value==="number"?value.toLocaleString("en",{useGrouping:!["league_trophies","builder_trophies"].includes(metric)}):value;
    const width=Math.max(1,...measured.map(row=>format(row.value).length));
    const metricIcons:Record<string,string>={league_trophies:"Legend I",builder_trophies:"builderRuby League I",experience:"xp",war_stars:"war_star",capital:"capital_gold"};
    rows = measured.map(({member,value},index)=>{
      const builderLeague=builderTiers.find(tier=>(member.builderBaseTrophies??member.versusTrophies??0)>=tier.trophy_start)?.name;
      const icon=metric==="league_trophies"?emoji.get(member.leagueTier?.name??member.league?.name??"Unranked"):
        metric==="builder_trophies"?emoji.get(`builder${builderLeague??""}`):emoji.get(metricIcons[metric]??member.townHallLevel??0);
      const content=metric==="name"?displayNameColumn(member.name,20):`${format(value).padStart(width)} ${displayNameColumn(member.name,15)}`;
      return `\`${String(index+1).padStart(2)}\` ${icon} \`${content}\``;
    });
  }
  let description = "",
    shown = 0;
  for (const line of rows.slice(0, limit)) {
    if (description.length + line.length + 1 > 3600) break;
    description += (description ? "\n" : "") + line;
    shown++;
  }
  const title = `${scope === "family" ? "Family" : (clans[0]?.name ?? "Clan")} (${label})`;
  const footer = `${action === "compo" && shown === rows.length ? "" : `${shown}/${rows.length} ${action === "compo" ? "groups" : "players"} | `}${members.length} members${failedClans ? ` | ${failedClans} clans unavailable` : ""}${failedPlayers ? ` | ${failedPlayers} profiles/stats unavailable` : ""}${metric === "location" ? " | Public ranking location only" : ""}`;
  const icon = emoji.component("refresh");
  const response = legacyMessage({
    allowed_mentions: { parse: [] },
    embeds: [
      {
        ...(scope === "clan"
          ? { author: { name: title, ...(clans[0]?.badgeUrls?.small ? { icon_url: clans[0].badgeUrls.small } : {}) } }
          : { title }),
        color,
        description: description || (failedClans || failedPlayers ? "Member data is unavailable. Try again." : "No members match these filters."),
        footer: { text: footer },
      },
    ],
    components: [
      actionRow({
        type: 3,
        custom_id: `ck:members:${scope}|${target}|${action}|${metric}|${hall}|${limit}|${order}|type`,
        placeholder: action === "compo" ? "Composition type" : "Sort by",
        options: action === "compo"
          ? Object.entries(groups).filter(([value])=>scope==="family"||value!=="location").map(([value,label])=>({label,value,default:value===metric}))
          : Object.entries(metrics).map(([value,rule])=>{
            const icons:Record<string,string|number>={townhall:18,name:18,tag:18,role:18,league_trophies:"Legend I",builder_trophies:"builderRuby League I",experience:"xp",war_stars:"war_star",capital:"capital_gold",heroes:"Barbarian King"};
            const icon=emoji.component(icons[value]!);
            return {label:rule.label,value,default:value===metric,...(icon?{emoji:icon}:{})};
          }),
      }),
      actionRow({
        type: 2,
        style: 2,
        emoji: icon ?? { name: "↻" },
        custom_id: `ck:members:${scope}|${target}|${action}|${metric}|${hall}|${limit}|${order}`,
      }),
    ],
  });
  return scope === "clan" ? withClanSelector(ctx, response) : response;
}
export async function dispatchMemberReport(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
) {
  const parts = (ctx.interaction.data?.custom_id ?? "")
    .slice("ck:members:".length)
    .split("|");
  const changingType = parts.length === 8 && parts.pop() === "type";
  const [scope, target, action, storedMetric, hall, limit, order] = parts;
  const metric = changingType ? ctx.interaction.data?.values?.[0] : storedMetric;
  if (
    parts.length !== 7 ||
    (changingType && (!["compo","sorted"].includes(action??"") || ctx.interaction.data?.values?.length !== 1 || !metric || !(metric in (action==="compo"?groups:metrics)))) ||
    !["clan", "family"].includes(scope ?? "") ||
    (scope === "family" && target !== ctx.interaction.guild_id)
  )
    throw new CommandInputError("Invalid member report.");
  const options = new Map(ctx.options);
  for (const [name, value] of [
    ["clan", target],
    [action === "compo" ? "type" : "sort_by", metric],
    ["sort_order", order],
  ] as const)
    options.set(name, { name, type: OptionType.String, value });
  options.set("townhall", {
    name: "townhall",
    type: OptionType.Integer,
    value: Number(hall),
  });
  options.set("limit", {
    name: "limit",
    type: OptionType.Integer,
    value: Number(limit),
  });
  const run = memberReport(
    { ...ctx, path: [action!], options },
    scope as Scope,
  );
  if (!waitUntil) return run;
  waitUntil(
    run
      .then((reply) =>
        ctx.services.discordRest.editOriginalInteractionResponse(
          ctx.interaction.token,
          reply.data ?? {},
        ),
      )
      .catch((error) =>
        sendInteractionError(ctx,error),
      ),
  );
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
