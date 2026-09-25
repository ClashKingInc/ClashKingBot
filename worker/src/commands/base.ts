import { actionRow, legacyMessage, type ActionRowComponent } from "../discord/components";
import { InteractionResponseType, InteractionType, type DiscordAttachment, type DiscordMessage } from "../discord/types";
import { localizations, translate, resolveLocale } from "../localization/catalog";
import { CommandInputError, invokingUserId, requireGuildId } from "./command-utils";
import { modalFields, textField } from "./modals";
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
  ephemeral: true,
  definition: {
    contexts: [0],
    description: translate("base.description"),
    description_localizations: localizations("base.description"),
    integration_types: [0],
    name: "base",
    name_localizations: localizations("base.name"),
    type: 1,
  },
  async execute(context) {
    requireGuildId(context);
    return { type: InteractionResponseType.Modal, data: {
      custom_id: "base:submit", title: translate("base.title", context.locale),
      components: [
        { type: 10, content: translate("base.help", context.locale) },
        textField("base_link", translate("base.link", context.locale), 4000),
        textField("description", translate("base.descriptionLabel", context.locale), 1000, true),
        { type: 18, label: translate("base.screenshots", context.locale), component: {
          type: 19, custom_id: "screenshots", min_values: 1, max_values: 4, required: true,
          file_types: [".png", ".jpg", ".jpeg", ".gif", ".webp"],
        } },
      ],
    } };
  },
};

export const submitBase: ComponentHandler = async (context) => {
    if (context.interaction.type !== InteractionType.ModalSubmit) {
      throw new CommandInputError(translate("error.invalidInteraction", context.locale));
    }
    const guildId = requireGuildId(context);
    const channelId = context.interaction.channel_id;
    if (!channelId) throw new CommandInputError(translate("base.missingChannel", context.locale));
    const fields = modalFields(context.interaction.data?.components);
    const rawLink = fields.get("base_link")?.value;
    const description = fields.get("description")?.value;
    if (!rawLink?.trim() || !description?.trim() || [...description].length > 1000) {
      throw new CommandInputError(translate("base.required", context.locale));
    }
    const baseLink = validBaseLink(rawLink, context.locale);
    const ids = fields.get("screenshots")?.values ?? [];
    if (ids.length < 1 || ids.length > 4 || new Set(ids).size !== ids.length) {
      throw new CommandInputError(translate("base.imagesRequired", context.locale));
    }
    const attachments = ids.map((id) => {
      const attachment = context.interaction.data?.resolved?.attachments?.[id];
      if (!attachment || !["image/png", "image/jpeg", "image/gif", "image/webp"].includes(attachment.content_type ?? "")
        || attachment.size <= 0 || attachment.size > 25 * 1024 * 1024) {
        throw new CommandInputError(translate("base.imageInvalid", context.locale));
      }
      return attachment;
    });
    // Sequential uploads bound memory use to one image and retain user-selected order.
    const images: UploadResponse[] = [];
    for (const attachment of attachments) {
      images.push(await conversionStep(translate("base.uploadFailed", context.locale), () => uploadImage(context, guildId, attachment)));
    }
    const base = await conversionStep(translate("base.postFailed", context.locale), () => context.services.api.post<BaseRecord>(`/v2/server/${guildId}/bases`, {
      baseLink, channelId, description, images: images.map((image) => image.url),
    }));
    const publicLocale = resolveLocale(context.interaction.guild_locale);
    if (!publicLocale.startsWith("en") && base.id && base.messageId) {
      // The API owns publication; only localize the existing controls, never repost.
      try {
        await context.services.discordRest.editChannelMessage(channelId, base.messageId, { components: baseButtons(base.id, publicLocale) });
      } catch {
        console.warn("Base published but button localization failed", { baseId: base.id, locale: publicLocale });
      }
    }
    return legacyMessage({ content: translate("base.posted", context.locale, { url: base.discordMessageUrl }) }, { ephemeral: true });
};

const recordDownload: ComponentHandler = async (context, segments) => {
  const baseId = requiredBaseId(segments, context.locale);
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
  const baseId = requiredBaseId(segments, context.locale);
  await prepareBaseForAction(context, baseId);
  const userId = invokingUserId(context);
  await context.services.api.put(`/v2/bases/${encodeURIComponent(baseId)}/votes/${userId}`, { direction });
  return legacyMessage({ content: translate(direction === "up" ? "base.upvote" : "base.downvote", context.locale) }, { ephemeral: true });
};

const convertLegacyBase: ComponentHandler = async (context, segments) => {
  const legacyAction = segments[0];
  if (legacyAction !== "link" && legacyAction !== "who") throw new CommandInputError(translate("base.invalidLegacyButton", context.locale));
  const base = await prepareBaseForAction(context);
  if (legacyAction === "link") return performDownload(context, base);
  return showLegacyDownloaders(context, base.id);
};

async function prepareBaseForAction(context: CommandContext, expectedBaseId?: string): Promise<LegacyBaseRecord> {
  const message = requiredLegacyMessage(context.interaction.message, context.locale);
  const guildId = requireGuildId(context);
  const channelId = context.interaction.channel_id ?? message.channel_id;
  if (!channelId) throw new CommandInputError(translate("base.missingMessageChannel", context.locale));

  const base = await conversionStep(
    translate("base.unavailable", context.locale),
    () => context.services.api.get<LegacyBaseRecord>(`/v2/bases/legacy/${message.id}`),
  );
  if (expectedBaseId !== undefined && base.id !== expectedBaseId) {
    throw new CommandInputError(translate("base.wrongMessage", context.locale));
  }
  if (!trustedLegacyBaseLink(base.baseLink)) {
    throw new CommandInputError(translate("base.invalidLegacyLink", context.locale));
  }
  if (base.serverId !== null || base.channelId !== null) {
    if (base.serverId !== guildId || base.channelId !== channelId) {
      throw new CommandInputError(translate("base.wrongLocation", context.locale));
    }
    return base;
  }

  const attachments = legacyImageAttachments(message);
  if (base.images.length === 0 && attachments.length === 0) {
    throw new CommandInputError(translate("base.missingImage", context.locale));
  }
  for (let index = 0; index < attachments.length; index++) {
    const attachment = attachments[index];
    if (!attachment) continue;
    await conversionStep(
      translate("base.copyFailed", context.locale),
      () => context.services.api.post(`/v2/bases/${base.id}/images/${index + 1}`, { sourceUrl: attachment.url }),
    );
  }

  await conversionStep(
    translate("base.updateFailed", context.locale),
    () => context.services.discordRest.editChannelMessage(channelId, message.id, { components: baseButtons(base.id, resolveLocale(context.interaction.guild_locale)) }),
  );
  const description = legacyDescription(message);
  await conversionStep(
    translate("base.finalizeFailed", context.locale),
    () => context.services.api.post(`/v2/bases/${base.id}/finalize`, {
      channelId, description, serverId: guildId,
    }),
  );
  return { ...base, channelId, description, serverId: guildId };
}

export const baseComponentHandlers: Array<[string, ComponentHandler]> = [
  ["base:submit", submitBase],
  ["base:link", recordDownload], ["base:upvote", recordVote("up")], ["base:downvote", recordVote("down")],
  ["base:legacy", convertLegacyBase],
];

async function showLegacyDownloaders(context: CommandContext, baseId: string) {
  const guildId = requireGuildId(context);
  const base = await context.services.api.get<BaseRecord>(`/v2/server/${guildId}/bases/${baseId}`);
  const empty = base.downloaders.length === 0;
  return legacyMessage({ embeds: [{
    color: empty ? 0xed4245 : 0x57f287,
    description: empty ? translate("base.noDownloads", context.locale) : base.downloaders.map((id) => `➼ <@${id}>`).join("\n"),
    ...(empty ? {} : { title: translate("base.downloads", context.locale) }),
  }] }, { ephemeral: true });
}

function baseButtons(baseId: string, locale: string): ActionRowComponent[] {
  return [actionRow(
    { custom_id: `base:link:${baseId}`, label: translate("base.getLink", locale), emoji: { name: "🔗" }, style: 1, type: 2 },
    { custom_id: `base:upvote:${baseId}`, emoji: { name: "👍" }, style: 2, type: 2 },
    { custom_id: `base:downvote:${baseId}`, emoji: { name: "👎" }, style: 2, type: 2 },
  )];
}

function requiredLegacyMessage(message: DiscordMessage | undefined, locale: string): DiscordMessage {
  if (!message) throw new CommandInputError(translate("base.missingMessage", locale));
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
    validBaseLink(value);
    return true;
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

async function uploadImage(context: CommandContext, guildId: string, attachment: DiscordAttachment): Promise<UploadResponse> {
  const image = await context.services.discordRest.download(attachment.url);
  const form = new FormData();
  form.set("file", image, attachment.filename);
  return context.services.api.postForm<UploadResponse>(`/v2/server/${guildId}/bases/images`, form);
}

function validBaseLink(value: string, locale = "en-US"): string {
  try {
    if (value.length > 8192) throw new Error("Link too long");
    const parsed = new URL(value.trim());
    // Keep normalization aligned with the API's base-link.ts boundary.
    if (parsed.protocol === "https:" && parsed.hostname === "link.clashofclans.com" && !parsed.port
      && !parsed.username && !parsed.password && /^\/(?:[a-z]{2}(?:-[a-z]{2})?)?\/?$/iu.test(parsed.pathname)
      && [...parsed.searchParams.keys()].every((key) => !["action", "id"].includes(key.toLowerCase()) || key === key.toLowerCase())
      && parsed.searchParams.getAll("action").length === 1 && parsed.searchParams.get("action") === "OpenLayout"
      && parsed.searchParams.getAll("id").length === 1 && /^[A-Za-z0-9:_-]{1,2048}$/u.test(parsed.searchParams.get("id") ?? "")) {
      return normalizedLayoutLink(parsed.toString());
    }
  } catch { /* handled below */ }
  throw new CommandInputError(translate("base.invalidLink", locale));
}

function normalizedLayoutLink(value: string): string {
  const parsed = new URL(value);
  const id = parsed.searchParams.get("id");
  return id ? `https://link.clashofclans.com/en?action=OpenLayout&id=${encodeURIComponent(id)}` : parsed.toString();
}

function requiredBaseId(segments: string[], locale: string): string {
  const value = segments[0];
  if (segments.length !== 1 || !value || !/^[1-9]\d*$/u.test(value) || BigInt(value) > 9_223_372_036_854_775_807n) {
    throw new CommandInputError(translate("base.invalidButton", locale));
  }
  return value;
}
