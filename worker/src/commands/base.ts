import { actionRow, legacyMessage, type ActionRowComponent } from "../discord/components";
import type { DiscordAttachment, DiscordMessage } from "../discord/types";
import { CommandInputError, OptionType, invokingUserId, requireGuildId, stringOption } from "./command-utils";
import type { Command, CommandContext, ComponentHandler } from "./types";

interface BaseRecord {
  baseLink: string;
  discordMessageUrl: string;
  downloadCount: number;
  downloaders: string[];
  downvotes: number;
  id: string;
  messageId: string;
  upvotes: number;
}

interface UploadResponse { filename: string; url: string }

interface LegacyBaseRecord {
  baseLink: string;
  channelId: string | null;
  description: string;
  id: string;
  images: string[];
  messageId: string;
  serverId: string | null;
}

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
      { description: "Description; use && for a new line", max_length: 1000, name: "description", required: true, type: OptionType.String },
      { description: "Screenshot of the base", name: "photo", required: true, type: OptionType.Attachment },
      { description: "Second screenshot of the base", name: "photo_2", type: OptionType.Attachment },
      { description: "Third screenshot of the base", name: "photo_3", type: OptionType.Attachment },
      { description: "Fourth screenshot of the base", name: "photo_4", type: OptionType.Attachment },
    ],
    type: 1,
  },
  async execute(context) {
    const guildId = requireGuildId(context);
    const channelId = context.interaction.channel_id;
    if (!channelId) throw new CommandInputError("Discord did not include a channel for this command.");
    const baseLink = validBaseLink(requiredString(context, "base_link"));
    const description = [...requiredString(context, "description")].slice(0, 1000).join("").replaceAll("&&", "\n");
    const attachments = [
      requiredAttachment(context, "photo"),
      ...["photo_2", "photo_3", "photo_4"].map((name) => attachmentOption(context, name)),
    ]
      .filter((attachment): attachment is DiscordAttachment => attachment !== undefined);
    const images = await Promise.all(attachments.map((attachment) => uploadImage(context, guildId, attachment)));
    const base = await context.services.api.post<BaseRecord>(`/v2/server/${guildId}/bases`, {
      baseLink, channelId, description, images: images.map((image) => image.url),
    });
    return legacyMessage({ content: `Base posted: ${base.discordMessageUrl}` }, { ephemeral: true });
  },
};

const recordDownload: ComponentHandler = async (context, segments) => {
  const baseId = requiredBaseId(segments);
  const base = await prepareBaseForAction(context, baseId);
  return performDownload(context, base);
};

async function performDownload(context: CommandContext, base: LegacyBaseRecord) {
  await context.services.api.postEmpty<{ downloadCount: number }>(
    `/v2/bases/${encodeURIComponent(base.id)}/downloaders/${invokingUserId(context)}`,
  );
  return legacyMessage({ content: normalizedLayoutLink(base.baseLink) }, { ephemeral: true });
}

const recordVote = (direction: "up" | "down"): ComponentHandler => async (context, segments) => {
  const baseId = requiredBaseId(segments);
  await prepareBaseForAction(context, baseId);
  const userId = invokingUserId(context);
  await context.services.api.put(`/v2/bases/${encodeURIComponent(baseId)}/votes/${userId}`, { direction });
  return legacyMessage({ content: direction === "up" ? "Upvote recorded." : "Downvote recorded." }, { ephemeral: true });
};

const convertLegacyBase: ComponentHandler = async (context, segments) => {
  const legacyAction = segments[0];
  if (legacyAction !== "link" && legacyAction !== "who") throw new CommandInputError("This legacy base button is invalid.");
  const base = await prepareBaseForAction(context);
  if (legacyAction === "link") return performDownload(context, base);
  return showLegacyDownloaders(context, base.id);
};

async function prepareBaseForAction(context: CommandContext, expectedBaseId?: string): Promise<LegacyBaseRecord> {
  const message = requiredLegacyMessage(context.interaction.message);
  const guildId = requireGuildId(context);
  const channelId = context.interaction.channel_id ?? message.channel_id;
  if (!channelId) throw new CommandInputError("Discord did not include the base message channel.");

  const base = await conversionStep(
    "This legacy base is not available for conversion.",
    () => context.services.api.get<LegacyBaseRecord>(`/v2/bases/legacy/${message.id}`),
  );
  if (expectedBaseId !== undefined && base.id !== expectedBaseId) {
    throw new CommandInputError("This base button does not belong to this message.");
  }
  if (!trustedLegacyBaseLink(base.baseLink)) {
    throw new CommandInputError("This legacy base has an invalid Clash of Clans layout link and was not converted.");
  }
  if (base.serverId !== null || base.channelId !== null) {
    if (base.serverId !== guildId || base.channelId !== channelId) {
      throw new CommandInputError("This base is already bound to a different Discord message location.");
    }
    return base;
  }

  const attachments = legacyImageAttachments(message);
  if (base.images.length === 0 && attachments.length === 0) {
    throw new CommandInputError("The original base image is no longer available, so this message cannot be converted.");
  }
  for (let index = 0; index < attachments.length; index++) {
    const attachment = attachments[index];
    if (!attachment) continue;
    await conversionStep(
      "The base image could not be copied into ClashKing storage. The message remains unconverted; please try again.",
      () => context.services.api.post(`/v2/bases/${base.id}/images/${index + 1}`, { sourceUrl: attachment.url }),
    );
  }

  await conversionStep(
    "Discord could not update the base message. The base remains unconverted; please try again.",
    () => context.services.discordRest.editChannelMessage(channelId, message.id, { components: baseButtons(base.id) }),
  );
  const description = legacyDescription(message);
  await conversionStep(
    "The base message was updated, but its conversion could not be finalized. Click one of its new buttons to retry.",
    () => context.services.api.post(`/v2/bases/${base.id}/finalize`, {
      channelId, description, serverId: guildId,
    }),
  );
  return { ...base, channelId, description, serverId: guildId };
}

export const baseComponentHandlers: Array<[string, ComponentHandler]> = [
  ["base:link", recordDownload], ["base:upvote", recordVote("up")], ["base:downvote", recordVote("down")],
  ["base:legacy", convertLegacyBase],
];

async function showLegacyDownloaders(context: CommandContext, baseId: string) {
  const guildId = requireGuildId(context);
  const base = await context.services.api.get<BaseRecord>(`/v2/server/${guildId}/bases/${baseId}`);
  const empty = base.downloaders.length === 0;
  return legacyMessage({ embeds: [{
    color: empty ? 0xed4245 : 0x57f287,
    description: empty ? "No Downloads Currently." : base.downloaders.map((id) => `➼ <@${id}>`).join("\n"),
    ...(empty ? {} : { title: "Base Downloads:" }),
  }] }, { ephemeral: true });
}

function baseButtons(baseId: string): ActionRowComponent[] {
  return [actionRow(
    { custom_id: `base:link:${baseId}`, label: "Open Layout", style: 1, type: 2 },
    { custom_id: `base:upvote:${baseId}`, label: "Upvote", style: 2, type: 2 },
    { custom_id: `base:downvote:${baseId}`, label: "Downvote", style: 2, type: 2 },
  )];
}

function requiredLegacyMessage(message: DiscordMessage | undefined): DiscordMessage {
  if (!message) throw new CommandInputError("Discord did not include the legacy base message.");
  return message;
}

function legacyImageAttachments(message: DiscordMessage): DiscordAttachment[] {
  return (message.attachments ?? []).slice(0, 4);
}

function legacyDescription(message: DiscordMessage): string {
  const content = message.content ?? "";
  if (content.trim()) return [...content].slice(0, 1000).join("");
  const description = message.embeds?.find((embed) => embed.description?.trim())?.description ?? "";
  return [...description].slice(0, 1000).join("");
}

function trustedLegacyBaseLink(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && parsed.hostname === "link.clashofclans.com";
  } catch {
    return false;
  }
}

async function conversionStep<T>(message: string, operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch {
    throw new CommandInputError(message);
  }
}

function attachmentOption(context: CommandContext, name: string): DiscordAttachment | undefined {
  const id = stringOption(context, name);
  if (!id) return undefined;
  const attachment = id ? context.interaction.data?.resolved?.attachments?.[id] : undefined;
  if (!attachment) throw new CommandInputError(`Discord did not include the ${name} attachment.`);
  if (!attachment.content_type?.startsWith("image/")) throw new CommandInputError("The base screenshot must be an image.");
  return attachment;
}

function requiredAttachment(context: CommandContext, name: string): DiscordAttachment {
  const attachment = attachmentOption(context, name);
  if (!attachment) throw new CommandInputError("A base screenshot is required.");
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
    if (parsed.origin === "https://link.clashofclans.com" && parsed.pathname === "/en" && parsed.hash === ""
      && [...parsed.searchParams.keys()].every((key) => key === "action" || key === "id")
      && parsed.searchParams.getAll("action").length === 1 && parsed.searchParams.get("action") === "OpenLayout"
      && parsed.searchParams.getAll("id").length === 1 && parsed.searchParams.get("id")?.trim()) return parsed.toString();
  } catch { /* handled below */ }
  throw new CommandInputError("Not a Valid Base Link");
}

function normalizedLayoutLink(value: string): string {
  const parsed = new URL(value);
  const id = parsed.searchParams.get("id");
  return id ? `https://link.clashofclans.com/en?action=OpenLayout&id=${encodeURIComponent(id)}` : parsed.toString();
}

function requiredString(context: CommandContext, name: string): string {
  const value = stringOption(context, name);
  if (!value) throw new CommandInputError(`Missing required option ${name}.`);
  return value;
}

function requiredBaseId(segments: string[]): string {
  const value = segments[0];
  if (segments.length !== 1 || !value || !/^[1-9]\d*$/u.test(value) || BigInt(value) > 9_223_372_036_854_775_807n) {
    throw new CommandInputError("This base button is invalid.");
  }
  return value;
}
