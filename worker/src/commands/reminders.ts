import { applicationEmojis } from "../discord/emojis";
import { InteractionResponseType, MessageFlags, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { escapeMarkdown } from "./game-common";
import type { Command, CommandContext } from "./types";

interface Member { tag: string; name: string; townHallLevel?: number; townhallLevel?: number; attacks?: unknown[] }
interface Side { tag: string; name: string; stars: number; members: Member[] }
interface War { state: string; startTime?: string; endTime: string; attacksPerMember?: number; clan: Side; opponent: Side }
interface Missing { tag: string; name: string; hall: number; count: string }
const timestamp = (raw: string) => Date.parse(raw.replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})\.\d{3}Z$/u, "$1-$2-$3T$4:$5:$6.000Z"));
const active = (war: War | undefined) => !!war &&
  (war.state === "inWar" || (war.state === "preparation" && !!war.startTime && Number.isFinite(timestamp(war.startTime)))) &&
  timestamp(war.endTime) > Date.now();

async function currentWar(ctx: CommandContext, tag: string): Promise<War> {
  const path = `/v2/bot/clash/clans/${encodeURIComponent(tag)}/currentwar`;
  const regular = await ctx.services.api.get<War>(path).catch(() => undefined);
  if (active(regular)) return regular!;
  // CWL is part of War, but has a separate upstream endpoint. Search newest
  // rounds first; never select another clan's or an already finished war.
  const group = await ctx.services.api.get<{ rounds?: Array<{ warTags: string[] }> }>(`${path}/leaguegroup`).catch(() => undefined);
  let preparation: War | undefined;
  for (const round of [...(group?.rounds ?? [])].reverse()) {
    const tags = round.warTags.filter(value => value !== "#0");
    for (let offset = 0; offset < tags.length; offset += 4) {
      const wars = await Promise.all(tags.slice(offset, offset + 4).map(value => ctx.services.api.get<War>(`/v2/bot/clash/clanwarleagues/wars/${encodeURIComponent(value)}`).catch(() => undefined)));
      for (const war of wars) {
        if (!active(war) || !war || (war.clan.tag !== tag && war.opponent.tag !== tag)) continue;
        // CWL rounds overlap. A running battle takes priority over the next
        // preparation day, even though newer rounds are fetched first.
        if (war.state === "inWar") return { ...war, attacksPerMember: 1 };
        if (!preparation || timestamp(war.startTime!) < timestamp(preparation.startTime!)) preparation = war;
      }
    }
  }
  if (preparation) return { ...preparation, attacksPerMember: 1 };
  throw new CommandInputError("No active war found for this clan.");
}

export const remindersCommand: Command = {
  deferred: true, ephemeral: true,
  definition: {
    name: "reminders", description: "Send a one-off reminder now", type: 1,
    contexts: [0], integration_types: [0], default_member_permissions: "32",
    options: [
      { name: "type", description: "Reminder to send", type: 3, required: true,
        choices: [{ name: "War & CWL", value: "War" }, { name: "Clan Games", value: "Clan Games" }, { name: "Raid Weekend", value: "Clan Capital" }] },
      { name: "clan", description: "Clan tag", type: 3, required: true },
      { name: "channel", description: "Destination (defaults to this channel)", type: 7 },
      { name: "custom_text", description: "Text to add below the reminder", type: 3, max_length: 500 },
    ],
  },
  async execute(ctx): Promise<DiscordInteractionResponse> {
    const serverId = requireGuildId(ctx);
    if ((BigInt(ctx.interaction.member?.permissions ?? "0") & 32n) === 0n) throw new CommandInputError("Manage Server permission is required.");
    const type = stringOption(ctx, "type"), tag = normalizeTag(stringOption(ctx, "clan") ?? "", ctx.locale);
    if (!["War", "Clan Capital", "Clan Games"].includes(type ?? "")) throw new CommandInputError("Choose War, Clan Games, or Raid Weekend.");
    const channelId = stringOption(ctx, "channel") ?? ctx.interaction.channel_id;
    if (!channelId) throw new CommandInputError("Choose a destination channel.");
    const channel = await ctx.services.discordRest.getChannel(channelId);
    if (channel.guild_id !== serverId || ![0, 5, 10, 11, 12].includes(channel.type)) throw new CommandInputError("Choose a text channel or thread in this server.");
    let heading: string, missing: Missing[];
    if (type === "War") {
      const war = await currentWar(ctx, tag), own = war.clan.tag === tag ? war.clan : war.opponent, other = own === war.clan ? war.opponent : war.clan;
      const total = war.attacksPerMember ?? 2;
      const preparing = war.state === "preparation";
      // Preparation reminders address the upcoming roster, not missed attacks.
      const used = (member: Member) => preparing ? 0 : member.attacks?.length ?? 0;
      missing = own.members.filter(member => used(member) < total).map(member => ({ ...member, hall: member.townhallLevel ?? member.townHallLevel ?? 0, count: `${total - used(member)}/${total}` }));
      const count = (side: Side) => side.members.reduce((sum, member) => sum + (member.attacks?.length ?? 0), 0);
      heading = preparing
        ? `⏰ **War starts <t:${Math.floor(timestamp(war.startTime!) / 1000)}:R>**\n📌 **${escapeMarkdown(own.name)} vs ${escapeMarkdown(other.name)}**\nPrepare for battle day.`
        : `⏰ **War ends <t:${Math.floor(timestamp(war.endTime) / 1000)}:R>**\n📌 **${escapeMarkdown(own.name)} vs ${escapeMarkdown(other.name)}**\n⚔️ ${count(own)}/${count(other)}  ⭐ ${own.stars}/${other.stars}`;
    } else {
      const clan = await ctx.services.api.get<{ name: string; memberList: Member[] }>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}`);
      if (type === "Clan Games") {
        const now = new Date(), start = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 22, 8), end = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 28, 8);
        if (Date.now() < start || Date.now() >= end) throw new CommandInputError("Clan Games is not ongoing.");
        const stats = await ctx.services.api.get<{ items: Array<{ tag: string; points: number }> }>(`/v2/bot/clans/${encodeURIComponent(tag)}/clan-games`);
        const points = new Map(stats.items.map(item => [item.tag, item.points]));
        missing = clan.memberList.filter(member => (member.townHallLevel ?? 0) >= 6 && (points.get(member.tag) ?? 0) < 4000).map(member => ({ ...member, hall: member.townHallLevel ?? 0, count: `${points.get(member.tag) ?? 0}/4,000` }));
        heading = `**${escapeMarkdown(clan.name)} Clan Games**\n⏰ Ends <t:${Math.floor(end / 1000)}:R>`;
      } else {
        interface Raid { state: string; endTime: string; members?: Array<{ tag: string; attacks: number; attackLimit: number; bonusAttackLimit: number }> }
        const raids = await ctx.services.api.get<{ items: Raid[] }>(`/v2/bot/clash/clans/${encodeURIComponent(tag)}/capitalraidseasons`, { limit: 1 });
        const raid = raids.items[0];
        if (!raid || raid.state !== "ongoing" || timestamp(raid.endTime) <= Date.now()) throw new CommandInputError("Raid Weekend is not ongoing.");
        const participants = new Map((raid.members ?? []).map(member => [member.tag, member]));
        missing = clan.memberList.filter(member => (member.townHallLevel ?? 0) > 5).flatMap(member => {
          const progress = participants.get(member.tag), used = progress?.attacks ?? 0, total = progress ? progress.attackLimit + progress.bonusAttackLimit : 6;
          return used >= total || used >= 5 ? [] : [{ ...member, hall: member.townHallLevel ?? 0, count: `${total - used}/${total}` }];
        });
        heading = `**${escapeMarkdown(clan.name)} Raid Weekend**\n⏰ Ends <t:${Math.floor(timestamp(raid.endTime) / 1000)}:R>\n⚔️ Minimum 5 attacks`;
      }
    }
    if (!missing.length) throw new CommandInputError("No reminder needed—everyone has completed their participation.");
    const emojis = await applicationEmojis(ctx.services.discordRest), lines: string[] = [], mentions: string[] = [];
    missing.sort((a, b) => b.hall - a.hall || a.name.localeCompare(b.name));
    // Hidden links stay hidden. Failed identity lookup leaves a visible player
    // row without a mention; membership is checked by the existing API route.
    for (let offset = 0; offset < missing.length; offset += 5) {
      lines.push(...await Promise.all(missing.slice(offset, offset + 5).map(async member => {
        const identity = await ctx.services.api.get<{ link: { userId: string } | null }>(`/v2/bot/players/${encodeURIComponent(member.tag)}/identity`, { serverId }).catch(() => undefined);
        const userId = identity?.link?.userId;
        if (userId) mentions.push(userId);
        return `(${member.count}) ${emojis.get(member.hall) || `TH${member.hall}`} ${escapeMarkdown(member.name)} | ${userId ? `<@${userId}>` : member.tag}`;
      })));
    }
    const custom = stringOption(ctx, "custom_text"), pages: string[] = [];
    let content = heading;
    for (const line of [...lines, ...(custom ? [custom] : [])]) {
      if (content.length + line.length + 1 > 2000) { pages.push(content); content = line; }
      else content += `\n${line}`;
    }
    pages.push(content);
    // Send directly, like legacy manual reminders. No saved configuration,
    // schedule or background worker; acknowledge only after Discord accepts.
    for (const page of pages) await ctx.services.discordRest.request(`/channels/${channelId}/messages`, {
      method: "POST", body: JSON.stringify({ content: page, allowed_mentions: { parse: [], users: [...new Set(mentions)] } }),
    });
    return { type: InteractionResponseType.ChannelMessageWithSource, data: { content: "Reminder sent.", flags: MessageFlags.Ephemeral } };
  },
};
