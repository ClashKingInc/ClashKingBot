import { sendInteractionError } from "./errors";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, } from "../discord/types";
import { CommandInputError, requireGuildId, stringOption } from "./command-utils";
import { clanSelector } from "./clan-selector";
import { emojis } from "./game-common";
import { compactTableRow, COMPACT_TABLE } from "./display-width";
import { serverEmbedColor } from "./embed-color";
import type { CommandContext } from "./types";

interface ClanMemberLink {
  name: string; tag: string; hidden: boolean; townHall: number | null;
  link: { userId: string; inServer: boolean; username: string | null; verified: boolean } | null;
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
    // Only current server members display Discord identity. Outside-server
    // and hidden links display the player tag without extra user lookups.
    const identity = member.link?.inServer ? member.link.username ?? "Unavailable" : member.tag;
    // Verification describes the account link, not server membership. An outside-server
    // account can still be verified; grouping and hidden identity stay independent.
    const status = member.link ? emoji.get(member.link.verified ? "account_verified" : "account_unverified") || (member.link.verified ? "✓" : "△") : "";
    const row = `${status ? `${status} ` : ""}\`${compactTableRow([String(member.townHall ?? "–").padStart(2), { value: member.name, width: 15 }, identity.startsWith("#") ? identity : { value: identity, width: 18 }], status ? COMPACT_TABLE.iconColumns : 0)}\``;
    if (member.link?.inServer) linked.push(row);
    else if (member.link || member.hidden) other.push(row);
    else unlinked.push(row);
  }
  const groups = [
    { title: "Linked & in server", rows: linked },
    { title: "Not in server or hidden", rows: other },
    { title: "Not linked", rows: unlinked },
  ];
  const author = { name: `${clan.name} (${clan.tag})`, ...(clan.badge ? { icon_url: clan.badge } : {}) };
  // Descriptions provide one continuous roster rather than field-sized
  // sections. Empty groups disappear; only Discord's 4,096-character hard
  // limit can require another embed, without repeating section headings.
  const lines = groups.filter(group => group.rows.length).flatMap(group => [
    `**${group.title}: ${group.rows.length}**`, ...group.rows, "",
  ]);
  const descriptions: string[] = [];
  let description = "";
  for (const line of lines) {
    if (description.length + line.length + 1 > 4096) {
      descriptions.push(description.trimEnd()); description = "";
    }
    description += `${line}\n`;
  }
  if (description.trim()) descriptions.push(description.trimEnd());
  const embeds = descriptions.map((description, index) => ({color,description,...(index === 0 ? {author} : {})}));
  const selector = clanSelector({ clans, selectedTag: clan.tag, page: selectorPage,
    customId: `ck:links:${serverId}:${clan.tag}:${selectorPage}` });
  return legacyMessage({ allowed_mentions: { parse: [] }, embeds, components: [selector.row, actionRow({ type: 2, style: 2,
    // Discord requires distinct custom IDs within a message. The selector and
    // refresh button share routing, but must not share their exact ID.
    custom_id: `ck:links:${serverId}:${clan.tag}:${selector.page}:refresh`,
    emoji: emoji.component("refresh") ?? { name: "↻" },
  })] });
}

export async function dispatchClanLinks(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  const match = /^ck:links:([0-9]{15,22}):(#[0289PYLQGRJCUV]+):([0-9]{1,6})(?::refresh)?$/u.exec(ctx.interaction.data?.custom_id ?? "");
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
    .catch((error) => sendInteractionError(ctx,error)).then(() => undefined));
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
