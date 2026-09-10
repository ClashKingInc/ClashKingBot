import { actionRow, legacyMessage, type ActionRowComponent } from "../discord/components";
import type { DiscordAttachment } from "../discord/types";
import { CommandInputError, OptionType, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import type { Command, CommandContext, ComponentHandler } from "./types";

interface BaseRecord {
  baseLink: string;
  discordMessageUrl: string;
  downloadCount: number;
  downloaders: string[];
  id: string;
  messageId: string;
}

interface UploadResponse { filename: string; url: string }

export const baseCommand: Command = {
  deferred: true,
  ephemeral: true,
  definition: {
    contexts: [0],
    description: "Post a base with link and keep track of downloads",
    integration_types: [0],
    name: "base",
    options: [
      { description: "Base link copied from Clash of Clans", name: "base_link", required: true, type: OptionType.String },
      { description: "Description; use && for a new line", max_length: 1900, name: "description", required: true, type: OptionType.String },
      { description: "Screenshot of the base", name: "photo", required: true, type: OptionType.Attachment },
    ],
    type: 1,
  },
  async execute(context) {
    const guildId = requireGuildId(context);
    const channelId = context.interaction.channel_id;
    if (!channelId) throw new CommandInputError("Discord did not include a channel for this command.");
    const baseLink = validBaseLink(requiredString(context, "base_link"));
    const description = requiredString(context, "description").slice(0, 1000).replaceAll("&&", "\n");
    const attachment = requiredAttachment(context, "photo");
    const image = await uploadImage(context, guildId, attachment);
    const base = await context.services.api.post<BaseRecord>(`/v2/server/${guildId}/bases`, {
      baseLink, channelId, description, images: [image.url],
    });
    await context.services.discordRest.editChannelMessage(channelId, base.messageId, {
      components: baseButtons(base.id, base.downloadCount),
    });
    return legacyMessage({ content: `Base posted: ${base.discordMessageUrl}` }, { ephemeral: true });
  },
};

const recordDownload: ComponentHandler = async (context, segments) => {
  const baseId = requiredSegment(segments);
  const result = await context.services.api.postEmpty<{ downloadCount: number }>(
    `/v2/bases/${encodeURIComponent(baseId)}/downloaders/${invokingUserId(context)}`,
  );
  const guildId = requireGuildId(context);
  const base = await context.services.api.get<BaseRecord>(`/v2/server/${guildId}/bases/${encodeURIComponent(baseId)}`);
  const channelId = context.interaction.channel_id;
  if (channelId) {
    await context.services.discordRest.editChannelMessage(channelId, context.interaction.message?.id ?? base.messageId, {
      components: baseButtons(baseId, result.downloadCount),
    });
  }
  return legacyMessage({ content: normalizedLayoutLink(base.baseLink) }, { ephemeral: true });
};

const showDownloaders: ComponentHandler = async (context, segments) => {
  const baseId = requiredSegment(segments);
  const guildId = requireGuildId(context);
  const base = await context.services.api.get<BaseRecord>(`/v2/server/${guildId}/bases/${encodeURIComponent(baseId)}`);
  const empty = base.downloaders.length === 0;
  return legacyMessage({ embeds: [{
    color: empty ? 0xed4245 : 0x57f287,
    description: empty ? "No Downloads Currently." : base.downloaders.map((id) => `➼ <@${id}>`).join("\n"),
    ...(empty ? {} : { title: "Base Downloads:" }),
  }] }, { ephemeral: true });
};

export const baseComponentHandlers: Array<[string, ComponentHandler]> = [
  ["base:download", recordDownload], ["base:who", showDownloaders],
];

function baseButtons(baseId: string, count: number): ActionRowComponent[] {
  return [actionRow(
    { custom_id: `ck:base:download:${baseId}`, emoji: { name: "🔗" }, label: "Link", style: 2, type: 2 },
    { custom_id: `ck:base:who:${baseId}`, emoji: { name: "📈" }, label: `${count} Downloads`, style: 2, type: 2 },
  )];
}

function requiredAttachment(context: CommandContext, name: string): DiscordAttachment {
  const id = stringOption(context, name);
  const attachment = id ? context.interaction.data?.resolved?.attachments?.[id] : undefined;
  if (!attachment) throw new CommandInputError("A base screenshot is required.");
  if (!attachment.content_type?.startsWith("image/")) throw new CommandInputError("The base screenshot must be an image.");
  return attachment;
}

async function uploadImage(context: CommandContext, guildId: string, attachment: DiscordAttachment): Promise<UploadResponse> {
  const image = await context.services.discordRest.download(attachment.url);
  const form = new FormData();
  form.set("file", image, attachment.filename);
  return context.services.api.postForm<UploadResponse>(`/v2/server/${guildId}/bases/images`, form);
}

function validBaseLink(value: string): string {
  try {
    const parsed = new URL(value);
    if (parsed.protocol === "https:" && parsed.hostname === "link.clashofclans.com" && parsed.searchParams.get("action") === "OpenLayout" && parsed.searchParams.get("id")) return parsed.toString();
  } catch { /* handled below */ }
  throw new CommandInputError("Not a Valid Base Link");
}

function normalizedLayoutLink(value: string): string {
  const parsed = new URL(value);
  return `https://link.clashofclans.com/en?action=OpenLayout&id=${encodeURIComponent(parsed.searchParams.get("id") ?? "")}`;
}

function requiredString(context: CommandContext, name: string): string {
  const value = stringOption(context, name);
  if (!value) throw new CommandInputError(`Missing required option ${name}.`);
  return value;
}

function requiredSegment(segments: string[]): string {
  const value = segments[0];
  if (!value) throw new CommandInputError("This base button is invalid.");
  return value;
}
