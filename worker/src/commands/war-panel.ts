import { InteractionResponseType, MessageFlags, type DiscordInteractionResponse } from "../discord/types";
import type { CommandContext } from "./types";
import { serverEmbedColor } from "./embed-color";

interface WarAttack { attackerTag: string; defenderTag: string; destructionPercentage: number; order: number; stars: number }
interface WarMember { attacks?: WarAttack[]; mapPosition: number; name: string; tag: string; townhallLevel: number }
interface WarSide { badgeUrls?: { large?: string; medium?: string }; destructionPercentage: number; members: WarMember[]; name: string; stars: number; tag: string }
interface War { attacksPerMember: number; clan: WarSide; endTime: string; opponent: WarSide; preparationStartTime: string; startTime: string; state: string; teamSize: number; type?: string }
interface WarPanelData { identity: string; war: War }

const relative = (raw: string): string => {
  const iso = raw.replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})\.\d{3}Z$/u, "$1-$2-$3T$4:$5:$6.000Z");
  const seconds = Date.parse(iso) / 1000;
  return Number.isFinite(seconds) ? `<t:${seconds}:R>` : "unknown";
};
const clanLink = (side: WarSide): string => `[**${side.name.replace(/[[\]*_`]/gu, "") }**](https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(side.tag)})`;
const ephemeral = (data: Record<string, unknown>): DiscordInteractionResponse => ({ type: InteractionResponseType.ChannelMessageWithSource, data: { ...data, flags: MessageFlags.Ephemeral } });

export async function warPanelComponentHandler(context: CommandContext, segments: string[]): Promise<DiscordInteractionResponse> {
  const [action, rawTag, prep] = segments;
  const guildId = context.interaction.guild_id;
  const messageId = context.interaction.message?.id;
  if (!guildId || !messageId || !action || !rawTag || !/^\d{10}$/u.test(prep ?? "")
    || !["refresh", "attacks", "defenses", "opponent"].includes(action) || !/^[A-Z0-9]{3,15}$/u.test(rawTag)) {
    return ephemeral({ content: "This war panel is invalid." });
  }
  let result: WarPanelData;
  try {
    result = await context.services.api.get<WarPanelData>(`/v2/bot/war-panel/${guildId}/${messageId}/${encodeURIComponent(`#${rawTag}`)}`);
  } catch {
    return ephemeral({ content: "This war panel is no longer active or its war is unavailable." });
  }
  if (result.identity !== `#${rawTag}v${result.war.clan.tag === `#${rawTag}` ? result.war.opponent.tag : result.war.clan.tag}-${prep}`) {
    return ephemeral({ content: "This war panel belongs to a different war." });
  }
  const war = result.war;
  const own = war.clan.tag === `#${rawTag}` ? war.clan : war.opponent;
  const other = own === war.clan ? war.opponent : war.clan;
  if (action === "opponent") {
    const tag = other.tag.slice(1);
    return ephemeral({ components: [{ type: 1, components: [
      { type: 2, style: 5, label: "Opponent Link", url: `https://link.clashofclans.com/en?action=OpenClanProfile&tag=${encodeURIComponent(other.tag)}` },
      { type: 2, style: 5, label: "Clash of Stats", url: `https://www.clashofstats.com/clans/${tag}/summary` },
      { type: 2, style: 5, label: "Chocolate Clash", url: `https://fwa.chocolateclash.com/cc_n/clan.php?tag=${tag}` },
    ] }] });
  }
  const color=await serverEmbedColor(context);
  if (action === "refresh") {
    const state = war.state === "preparation" ? "In Prep" : war.state === "warEnded" ? "War Over" : "In War";
    const when = war.state === "preparation" ? `Starting: ${relative(war.startTime)}` : war.state === "warEnded" ? `Ended: ${relative(war.endTime)}` : `Ending: ${relative(war.endTime)}`;
    const count = (side: WarSide) => side.members.reduce((total, member) => total + (member.attacks?.length ?? 0), 0);
    const maximum = war.teamSize * war.attacksPerMember;
    const composition = (side: WarSide) => {
      const counts = new Map<number, number>();
      for (const member of side.members) counts.set(member.townhallLevel, (counts.get(member.townhallLevel) ?? 0) + 1);
      return [...counts].sort((a, b) => b[0] - a[0]).map(([level, amount]) => `TH${level} \`${amount}\``).join(" ");
    };
    const recent = [...own.members.flatMap((member) => (member.attacks ?? []).map((attack) => ({ member, attack, defense: false }))),
      ...other.members.flatMap((member) => (member.attacks ?? []).map((attack) => ({ member, attack, defense: true })))]
      .sort((a, b) => b.attack.order - a.attack.order).slice(0, 5)
      .map(({ member, attack, defense }) => `${defense ? "🛡️" : "⚔️"}\`${attack.destructionPercentage}%\` ${"★".repeat(attack.stars)}${"☆".repeat(3 - attack.stars)} \`${member.name}\``).join("\n");
    return { type: InteractionResponseType.UpdateMessage, data: { embeds: [{
      color,
      description: clanLink(own), thumbnail: { url: own.badgeUrls?.large ?? own.badgeUrls?.medium },
      footer: { text: `${war.type ?? "Regular"} War` },
      fields: [
        { name: "War Against", value: clanLink(other) },
        { name: "War State", value: `${state} (${war.teamSize} vs ${war.teamSize})\n${when}\n[*View War Timeline*](https://api.clashk.ing/timeline/${encodeURIComponent(own.tag)})` },
        { name: "War Stats", value: `${count(own)}/${maximum} ⚔️ ${count(other)}/${maximum}\n${own.stars} ★ ${other.stars}\n${own.destructionPercentage.toFixed(2)}% 🗡️ ${other.destructionPercentage.toFixed(2)}%` },
        { name: "War Composition", value: `${own.name}\n${composition(own)}\n${other.name}\n${composition(other)}` },
        ...(recent ? [{ name: "Last 5 attacks/defenses", value: recent.slice(0, 1024) }] : []),
      ],
    }] } };
  }
  const byTag = new Map([...own.members, ...other.members].map((member) => [member.tag, member]));
  const lines: string[] = [];
  const missing: string[] = [];
  for (const member of own.members) {
    const attacks = action === "attacks" ? member.attacks ?? [] : other.members.flatMap((opponent) => opponent.attacks ?? []).filter((attack) => attack.defenderTag === member.tag);
    if (attacks.length === 0) { missing.push(`➼ TH${member.townhallLevel} ${member.name}`); continue; }
    lines.push(`\nTH${member.townhallLevel} **${member.name}**`);
    for (const attack of attacks) {
      const base = byTag.get(action === "attacks" ? attack.defenderTag : attack.attackerTag)?.mapPosition;
      lines.push(`➼ ${attack.destructionPercentage}%${"★".repeat(attack.stars)}${"☆".repeat(3 - attack.stars)}${base ? ` (${base})` : ""}`);
    }
  }
  const title = `${own.name} ${action === "attacks" ? "War Attacks" : "Defenses Taken"}`;
  const description = lines.join("\n");
  const embeds = (description.match(/[\s\S]{1,3500}/gu) ?? ["No attacks yet."]).map((value, index) => ({ title: index ? `${title} (continued)` : title, description: value, color,
    thumbnail: own.badgeUrls?.large ? { url: own.badgeUrls.large } : undefined }));
  if (missing.length) embeds.push({ title: action === "attacks" ? "No attacks done" : "No defenses taken", description: missing.join("\n").slice(0, 3500), color, thumbnail: undefined });
  return ephemeral({ embeds: embeds.slice(0, 10) });
}

export async function dispatchWarPanel(context: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  const run = () => warPanelComponentHandler(context, (context.interaction.data?.custom_id ?? "").split(":").slice(2));
  if (!waitUntil) return run();
  waitUntil(run().then(response => response.type === InteractionResponseType.UpdateMessage
    ? context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, response.data ?? {})
    : context.services.discordRest.createInteractionFollowup(context.interaction.token, response.data ?? {}))
    .catch(() => context.services.discordRest.createInteractionFollowup(context.interaction.token, { content: "Could not load this war panel. Try again.", flags: MessageFlags.Ephemeral })));
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
