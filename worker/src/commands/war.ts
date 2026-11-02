import { sendInteractionError } from "./errors";
import { warSearchView, warViews } from "./war-search-view";
import { cwlSearch } from "./cwl-search";
import { warPreference } from "./war-preference";
import { withClanSelector } from "./clan-controls";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType } from "../discord/types";
import {
  CommandInputError,
  OptionType,
  normalizeTag,
  stringOption,
} from "./command-utils";
import { familyCwl } from "./cwl-family";
import { clanCommand } from "./clan";
import { emojis, subcommand } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import {
  compactWarTime,
  isWar,
  loadCurrentWar,
  warTime,
  type War,
} from "./war-data";
import type { Command, CommandContext } from "./types";

const clanOption = {
  name: "clan",
  description: "Clan tag or name",
  type: OptionType.String,
  required: true,
  autocomplete: true,
};
const views:readonly string[] = warViews.map(v=>v[0]);
interface ClanInfo {
  name: string;
  isWarLogPublic?: boolean;
  badgeUrls?: { small?: string };
}

const warSuggestions=new Map<string,{until:number;pending:Promise<War[]>}>();
// Coalesce keystrokes and keep only a short-lived, environment-scoped history.
// A failed lookup is evicted so it cannot poison subsequent autocomplete.
function storedWarSuggestions(ctx:CommandContext,tag:string){
 const key=`${ctx.env.CLASHKING_API_BASE_URL}:${ctx.env.DISCORD_APPLICATION_ID}:${tag}`,now=Date.now(),cached=warSuggestions.get(key);
 if(cached&&cached.until>now)return cached.pending;
 const pending=ctx.services.api.get<{items:War[]}>(`/v2/clan/${encodeURIComponent(tag)}/wars`,{limit:25},AbortSignal.timeout(1800)).then(result=>result.items.filter(w=>isWar(w,tag)&&Number.isFinite(warTime(w.endTime))));
 const entry={until:now+90_000,pending};
 pending.catch(()=>{if(warSuggestions.get(key)===entry)warSuggestions.delete(key);});
 if(warSuggestions.size>=128)warSuggestions.delete(warSuggestions.keys().next().value!);
 warSuggestions.set(key,entry);return pending;
}
export const warCommand: Command = {
  deferred: true,
  definition: {
    name: "war",
    description: "Current or recorded clan wars",
    type: 1,
    integration_types: [0, 1],
    contexts: [0, 1, 2],
    options: [
      {name:"preference",description:"Clan war preferences and recorded history",type:OptionType.Subcommand,options:[clanOption]},
      {
        name: "search",
        description: "Show a clan's current or recorded war",
        type: OptionType.Subcommand,
        options: [
          clanOption,
          {
            name: "war_end",
            description: "Recorded war end time (pick a suggestion)",
            type: OptionType.String,
            autocomplete: true,
          },
        ],
      },
    ],
  },
  async autocomplete(context) {
    const ctx = subcommand(context);
    if (ctx.options.get("war_end")?.focused) {
      const raw = stringOption(ctx, "clan");
      if (!raw) return [];
      const tag = normalizeTag(raw, ctx.locale);
      const query=String(ctx.options.get("war_end")?.value??"").toLocaleLowerCase();
      const current={name:"Current war",value:"current"};
      const wars=await storedWarSuggestions(ctx,tag).catch(()=>[]);
      const seen=new Set<string>();
      const choices=wars.sort((a,b)=>warTime(b.endTime)-warTime(a.endTime)).flatMap(war=>{
        const value=compactWarTime(war.endTime);if(seen.has(value))return [];seen.add(value);
        const enemy=war.clan.tag===tag?war.opponent:war.clan;
        const days=Math.floor(Math.max(0,Date.now()-warTime(war.endTime))/86400000);
        const ago=days?`${days}d ago`:`${Math.floor(Math.max(0,Date.now()-warTime(war.endTime))/3600000)}h ago`;
        const prep=war.startTime?warTime(war.startTime)-warTime(war.preparationStartTime):0;
        const type=war.tag||war.attacksPerMember===1?"CWL":[5,15,30,60,120,240,360,480,720,960,1200,1440].includes(prep/60000)?"Friendly":"Regular";
        const name=`${enemy.name} | ${ago} | ${type} | ${new Date(warTime(war.endTime)).toISOString().slice(0,10)}`.slice(0,100);
        return name.toLocaleLowerCase().includes(query)?[{name,value}]:[];
      });
      return [...(!query||current.name.toLocaleLowerCase().includes(query)?[current]:[]),...choices].slice(0,25);
    }
    return clanCommand.autocomplete!(context);
  },
  async execute(context) {
    const ctx = subcommand(context);
    if(ctx.path[0]==="preference")return withClanSelector(context,await warPreference(ctx));
    const tag = normalizeTag(stringOption(ctx, "clan") ?? "", ctx.locale),
      end = stringOption(ctx, "war_end") ?? "current";
    if (
      end !== "current" &&
      (!/^\d{8}T\d{6}\.\d{3}Z$/u.test(end) ||
        !Number.isFinite(warTime(end)) ||
        compactWarTime(end) !== end)
    )
      throw new CommandInputError("Choose a recorded war end time.");
    const settings = readSettings(ctx),
      clan = await ctx.services.api.get<ClanInfo>(
        `/v2/bot/clash/clans/${encodeURIComponent(tag)}`,
      );
    if (end !== "current") {
      const war = await ctx.services.api.get<War>(
        `/v2/war/${encodeURIComponent(tag)}/previous/${end}`,
      );
      if (!isWar(war, tag))
        throw new CommandInputError(
          "That recorded war does not contain this clan.",
        );
      return warReply(ctx, tag, war, Boolean(war.tag||war.attacksPerMember===1), end, settings);
    }
    const result = await loadCurrentWar(ctx, tag);
    if (!result.war)
      return legacyMessage({
        embeds: [
          {
            title: clan.name,
            description:
              result.privateLog || clan.isWarLogPublic === false
                ? "The war log is private and no matching war is available."
                : "No active war is available.",
            color: await serverEmbedColor(ctx),
          },
        ],
        components: await controls(ctx, "war", tag, end, settings),
      });
    return warReply(ctx, tag, result.war, result.cwl, end, settings);
  },
};
export const cwlCommand: Command = {
  deferred: true,
  definition: {
    name: "cwl",
    description: "Clan War League rounds and standings",
    type: 1,
    integration_types: [0, 1],
    contexts: [0, 1, 2],
    options: [
      {
        name: "rankings",
        description: "CWL status and standings across linked family clans",
        type: OptionType.Subcommand,
        options: [
          {
            name: "season",
            description: "Season YYYY-MM (defaults to current)",
            type: OptionType.String,
            autocomplete: true,
          },
        ],
      },
      {
        name: "search",
        description: "Show current or recorded Clan War League rounds",
        type: OptionType.Subcommand,
        options: [
          clanOption,
          {
            name: "season",
            description: "Season YYYY-MM (defaults to current)",
            type: OptionType.String,
            autocomplete: true,
          },
        ],
      },
    ],
  },
  async autocomplete(context) {
    const ctx=subcommand(context);
    if(!ctx.options.get("season")?.focused)return clanCommand.autocomplete!(context);
    const query=stringOption(ctx,"season")??"";
    return Array.from({length:25},(_,index)=>{
      const date=new Date();date.setUTCDate(1);date.setUTCMonth(date.getUTCMonth()-index);
      const value=date.toISOString().slice(0,7);return {name:date.toLocaleDateString("en",{month:"long",year:"numeric",timeZone:"UTC"}),value};
    }).filter(option=>!query||option.value.includes(query)||option.name.toLowerCase().includes(query.toLowerCase()));
  },
  async execute(context) {
    const ctx = subcommand(context);
    if (ctx.path[0] === "rankings")
      return familyCwl(ctx);
    return cwlSearch(ctx);
  },
};
function readSettings(ctx: CommandContext) {
  const view=stringOption(ctx,"view")??"overview",page=Number(ctx.options.get("round")?.value??0);
  if(!views.includes(view)||!Number.isInteger(page)||page<0||page>1000)throw new CommandInputError("Choose a valid war view.");
  return {view,limit:50,page};
}
async function controls(
  ctx: CommandContext,
  kind: string,
  tag: string,
  period: string,
  settings: { view: string; limit: number },
  round = 0,
) {
  const icon = (await emojis(ctx)).component("refresh");
  return [
    actionRow({
      type: 2,
      style: 2,
      emoji: icon ?? { name: "↻" },
      custom_id: `ck:war:${kind}|${tag}|${period}|${settings.view}|${settings.limit}|${round}`,
    }),
  ];
}
async function warReply(ctx:CommandContext,tag:string,war:War,cwl:boolean,period:string,settings:{view:string;limit:number;page:number}){
 return warSearchView(ctx,tag,war,cwl,period,settings.view,settings.page);
}
export async function dispatchWar(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
) {
  const parts = (ctx.interaction.data?.custom_id ?? "")
    .slice("ck:war:".length)
    .split("|");
  const [kind, clan, period, view, limit, round] = parts;
  if (parts.length === 6 && kind === "family") {
    if (
      clan !== ctx.interaction.guild_id ||
      period !== "rankings"
    )
      throw new CommandInputError("This report belongs to a different server.");
    const run = familyCwl({
      ...ctx,
      path: [period!],
      options: new Map([
        ["season", { name: "season", type: OptionType.String, value: view }],
        [
          "limit",
          { name: "limit", type: OptionType.Integer, value: Number(limit) },
        ],
        [
          "sort_order",
          { name: "sort_order", type: OptionType.String, value: round },
        ],
      ]),
    });
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
  if (
    parts.length !== 6 ||
    !["war", "cwl"].includes(kind ?? "") ||
    !clan ||
    !period
  )
    throw new CommandInputError("Invalid war control.");
  const selectedView=view==="select"?ctx.interaction.data?.values?.[0]:view;
  if(!selectedView||!views.includes(selectedView))throw new CommandInputError("Choose a war view.");
  const options = [
    { name: "clan", type: OptionType.String, value: clan },
    {
      name: kind === "war" ? "war_end" : "season",
      type: OptionType.String,
      value: period,
    },
    { name: "view", type: OptionType.String, value: selectedView },
    { name: "limit", type: OptionType.Integer, value: Number(limit) },
    { name: "round", type: OptionType.Integer, value: Number(round) },
  ];
  const command = kind === "war" ? warCommand : cwlCommand;
  const run = command.execute({
    ...ctx,
    options: new Map([
      ["search", { name: "search", type: OptionType.Subcommand, options }],
    ]),
  });
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
