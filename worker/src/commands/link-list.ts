import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, MessageFlags } from "../discord/types";
import { CommandInputError, requireGuildId, stringOption } from "./command-utils";
import { clanSelector } from "./clan-selector";
import { emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { CommandContext } from "./types";

interface ClanMemberLink {
  name: string; tag: string; hidden: boolean;
  link: { userId: string; inServer: boolean; username: string | null } | null;
}
interface LinkedClan { name: string; tag: string; badge: string | null; verified: boolean; members: ClanMemberLink[] }
interface ClanLinks { clans: LinkedClan[] }
const load = (ctx: CommandContext) => ctx.services.api.get<ClanLinks>(`/v2/links/server/${requireGuildId(ctx)}/clans`);

export async function clanLinksAutocomplete(ctx: CommandContext) {
  const query = (stringOption(ctx, "clan") ?? "").toLocaleLowerCase();
  const { clans } = await load(ctx);
  return clans.filter(clan => `${clan.name} ${clan.tag}`.toLocaleLowerCase().includes(query))
    .slice(0, 25).map(clan => ({ name: `${clan.name} | ${clan.tag}`.slice(0, 100), value: clan.tag }));
}

export async function clanLinkList(ctx: CommandContext, selectedTag = stringOption(ctx, "clan"), selectorPage = 0) {
  const serverId = requireGuildId(ctx);
  const [{ clans }, emoji, color] = await Promise.all([load(ctx), emojis(ctx), serverEmbedColor(ctx)]);
  if (!clans.length) return legacyMessage({ content: "No clans are linked to this server.", allowed_mentions: { parse: [] } });
  const clan = selectedTag ? clans.find(item => item.tag === selectedTag) : clans[0];
  if (!clan) throw new CommandInputError("Choose a clan linked to this server.");
  const linked: string[] = [], unlinked: string[] = [], other: string[] = [];
  for (const member of clan.members) {
    const name = escapeMarkdown([...member.name].slice(0, 25).join(""));
    const player = `**${name}** · \`${member.tag}\``;
    // The API is the visibility authority. Hidden identities are absent unless
    // this clan is verified; never reconstruct an owner from another endpoint.
    if (member.link?.inServer) linked.push(`${player} — <@${member.link.userId}>`);
    else if (member.link) other.push(`${player} — <@${member.link.userId}>`);
    else if (member.hidden) other.push(`${player} — Hidden account`);
    else unlinked.push(player);
  }
  const groups = [
    { title: "Linked in this server", rows: linked, empty: "No linked server members." },
    { title: "Unlinked", rows: unlinked, empty: "Everyone is linked." },
    { title: "Other linked accounts", rows: other, empty: "No links outside this server or hidden accounts." },
  ];
  const selector = clanSelector({ clans, selectedTag: clan.tag, page: selectorPage,
    customId: `ck:links:${serverId}:${clan.tag}:${selectorPage}` });
  return legacyMessage({ allowed_mentions: { parse: [] }, embeds: groups.map((group, index) => ({
    color, title: `${group.title} · ${group.rows.length}`, description: group.rows.join("\n") || group.empty,
    ...(index === 0 ? { author: { name: `${clan.name} · Discord links`, ...(clan.badge ? { icon_url: clan.badge } : {}) } } : {}),
  })), components: [selector.row, actionRow({ type: 2, style: 2,
    custom_id: `ck:links:${serverId}:${clan.tag}:${selector.page}`,
    emoji: emoji.component("refresh") ?? { name: "↻" },
  })] });
}

export async function dispatchClanLinks(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  const match = /^ck:links:([0-9]{15,22}):(#[0289PYLQGRJCUV]+):([0-9]{1,6})$/u.exec(ctx.interaction.data?.custom_id ?? "");
  if (!match || match[1] !== requireGuildId(ctx)) throw new CommandInputError("This list belongs to another server.");
  let tag = match[2]!, page = Number(match[3]);
  const value = ctx.interaction.data?.values?.[0];
  if (value?.startsWith("page:")) {
    if (!/^page:[0-9]{1,6}$/u.test(value)) throw new CommandInputError("Choose a valid clan page.");
    page = Number(value.slice(5));
  } else if (value) tag = value;
  const pending = clanLinkList(ctx, tag, page);
  if (!waitUntil) { const response = await pending; return { ...response, type: InteractionResponseType.UpdateMessage }; }
  waitUntil(pending.then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {}))
    .catch(() => ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token, {
      content: "Could not refresh this clan’s links. Try again shortly.", flags: MessageFlags.Ephemeral,
    })).then(() => undefined));
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
