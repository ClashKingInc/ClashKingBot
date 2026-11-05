import { actionRow, legacyMessage } from "../discord/components";
import {
  CommandInputError,
  requireGuildId,
  stringOption,
} from "./command-utils";
import { emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { cwlRanking, cwlStatus, loadCwl, type War } from "./war-data";
import type { CommandContext } from "./types";

interface Clan {
  name: string;
  tag: string;
  warLeague?: { id: number; name: string };
}
interface Row {
  clan: Clan;
  state?: string;
  rank?: number;
  stars?: number;
  unavailable?: boolean;
}
export async function familyCwl(ctx: CommandContext) {
  const guild = requireGuildId(ctx),
    action = ctx.path[0],
    season = stringOption(ctx, "season") ?? "current";
  if (
    action !== "rankings" ||
    (season !== "current" && !/^\d{4}-(0[1-9]|1[0-2])$/u.test(season))
  )
    throw new CommandInputError("Choose valid CWL report options.");
  const linked = await ctx.services.api.get<
    Array<{ tag: string; name: string }>
  >(`/v2/server/${guild}/clans-basic`);
  if (!linked.length)
    throw new CommandInputError("No family clans are linked to this server.");
  if (linked.length > 200)
    throw new CommandInputError(
      "This family is too large for one CWL report (maximum 200 clans).",
    );
  const rows: Row[] = [],
    warCache = new Map<string, Promise<War[]>>();
  for (let i = 0; i < linked.length; i += 4)
    rows.push(
      ...(await Promise.all(
        linked.slice(i, i + 4).map(async (reference) => {
          let clan: Clan = { ...reference };
          try {
            clan = await ctx.services.api.get<Clan>(
              `/v2/bot/clash/clans/${encodeURIComponent(reference.tag)}`,
            );
            if((season==="current"||season===new Date().toISOString().slice(0,7))&&await cwlStatus(ctx,clan.tag)==="spinning")return {clan,state:"spinning"};
            const data = await loadCwl(
              ctx,
              clan.tag,
              season === "current" ? undefined : season,
              warCache,
            );
            if (data?.group.warLeague)
              clan = {
                ...clan,
                warLeague: {
                  id: data.group.warLeague.id ?? 0,
                  name: data.group.warLeague.name,
                },
              };
            const score =
              data &&
              cwlRanking(data.group, data.wars).find(
                ([tag]) => tag === clan.tag,
              )?.[1];
            return {
              clan,
              ...(score && data?.wars.some(war=>war.state!=="preparation")
                ? { rank: score.rank, stars: score.stars, state:data.group.state }
                : { state: data?.group.state??"No available group" }),
            };
          } catch {
            return { clan, unavailable: true };
          }
        }),
      )),
    );
  rows.sort((a, b) => {
    const league = (a.clan.warLeague?.id ?? 0) - (b.clan.warLeague?.id ?? 0);
    return (
      -league ||
      (a.rank ?? Infinity) - (b.rank ?? Infinity) ||
      a.clan.name.localeCompare(b.clan.name)
    );
  });
  const emoji = await emojis(ctx),
    states: Record<string, string> = {
      spinning: "Spinning",
      inWar: "In war",
      preparation: "Preparation",
      ended: "Ended",
      warEnded: "Ended",
      notInWar: "Not participating",
      unavailable: "No available group",
    };
  let description = "",
    shown = 0;
  const visible=rows.filter(row=>row.state&&row.state!=="No available group");
  const statusIcons:Record<string,string>={spinning:"animated_clash_swords",preparation:"green_check",inWar:"wood_swords",ended:"green_check",warEnded:"green_check"};
  for (const row of visible) {
    const detail = row.unavailable
      ? "Unavailable — retry later"
      : row.rank
        ? `${emoji.get("trophy")} #${row.rank} ${emoji.get("war_star")} ${row.stars} | ${emoji.get(statusIcons[row.state??""]??"")} ${states[row.state??""]??row.state??""}`
        : `${emoji.get(statusIcons[row.state??""]??"")} ${states[row.state??""]??row.state??""}`;
    const line = `**${escapeMarkdown(row.clan.name)}**
${emoji.get(row.clan.warLeague?.name ?? "Unranked")} ${escapeMarkdown(row.clan.warLeague?.name ?? "Unranked")}\n${detail}`;
    if (description.length + line.length + 2 > 3800) break;
    description += (description ? "\n\n" : "") + line;
    shown++;
  }
  const refresh = emoji.component("refresh"), server=await ctx.services.discordRest.getGuild(guild);
  return legacyMessage({
    allowed_mentions: { parse: [] },
    embeds: [
      {
        author: {name:`${server.name} (CWL)`,...(typeof server.icon==="string"?{icon_url:`https://cdn.discordapp.com/icons/${guild}/${server.icon}.png`}:{})},
        description:description||"No CWL groups available for this season.",
        color: await serverEmbedColor(ctx),
        footer: {
          text: `${season === "current" ? new Date().toISOString().slice(0, 7) : season} | ${shown} clans`,
        },
      },
    ],
    components: [
      actionRow({
        type: 2,
        style: 2,
        emoji: refresh??{name:"↻"},
        custom_id: `ck:war:family|${guild}|${action}|${season}|200|desc`,
      }),
    ],
  });
}
