import { invokingUserId } from "./command-utils";
import { actionRow, legacyMessage } from "../discord/components";
import { emojis, escapeMarkdown } from "./game-common";
import type { Command } from "./types";
interface Status {
  configuredServers: number;
  familyClans: number;
  cachedGuilds: number;
  readyGuilds: number;
  expectedShards: number;
  healthyShards: number;
  serverMembers?: number;
  tickets?: number;
  players: number;
  clans: number;
  wars: number;
  countsRefreshedAt: string;
  observedAt: string;
}
export const botInfoCommand: Command = {
  deferred: true,
  definition: {
    name: "bot",
    description: "ClashKing statistics and useful links",
    type: 1,
    contexts: [0, 1, 2],
    integration_types: [0, 1],
  },
  async execute(ctx) {
    let data: Status;
    try {
      data = await ctx.services.api.get<Status>("/v2/bot/status", {}, AbortSignal.timeout(8000));
    } catch {
      return legacyMessage({ content: "Bot statistics are temporarily unavailable. Try again later." });
    }
    const [bot, icons] = await Promise.all([
      ctx.services.discordRest.getUser(ctx.env.DISCORD_APPLICATION_ID).catch(() => undefined),
      emojis(ctx),
    ]);
    const number = (value: number) => value.toLocaleString("en");
    const name = bot?.username || "ClashKing";
    const avatar = bot?.avatar
      ? `https://cdn.discordapp.com/avatars/${bot.id}/${bot.avatar}.png?size=128`
      : undefined;
    // Retain the old command's useful identity and community totals, without
    // presenting HTTP latency or isolate lifetime as gateway latency/uptime.
    const fields = [
      { name: "Bot", value: `<@${ctx.env.DISCORD_APPLICATION_ID}>`, inline: true },
      { name: "Servers", value: number(data.cachedGuilds), inline: true },
      { name: "Linked clans", value: number(data.familyClans), inline: true },
      ...(data.serverMembers === undefined ? [] : [{ name: "Server members", value: number(data.serverMembers), inline: true }]),
      ...(data.tickets === undefined ? [] : [{ name: "Tickets recorded", value: number(data.tickets), inline: true }]),
      ...(data.expectedShards > 0 ? [{ name: "Shards online", value: `${number(data.healthyShards)} / ${number(data.expectedShards)}`, inline: true }] : []),
      { name: "Players tracked", value: number(data.players), inline: true },
      { name: "Clans tracked", value: number(data.clans), inline: true },
      { name: "Wars recorded", value: number(data.wars), inline: true },
    ];
    const invite = new URL("https://discord.com/oauth2/authorize");
    invite.search = new URLSearchParams({ client_id: ctx.env.DISCORD_APPLICATION_ID, permissions: "8", scope: "bot applications.commands" }).toString();
    const refresh = icons.component("refresh") ?? { name: "↻" };
    return legacyMessage({
      allowed_mentions: { parse: [] },
      embeds: [{
        title: `${escapeMarkdown(name)} Statistics`,
        color: 0x2eb67d,
        ...(avatar ? { thumbnail: { url: avatar } } : {}),
        fields,
      }],
      components: [actionRow(
        { type: 2, style: 2, emoji: refresh, custom_id: `ck:page:bi:${invokingUserId(ctx)}:0` },
        { type: 2, style: 5, label: "Bot Invite", url: invite.href },
        { type: 2, style: 5, label: "Support Server", url: "https://discord.gg/gChZm3XCrS" },
      )],
    });
  },
};
