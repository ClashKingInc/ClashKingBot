import { ClashKingApiError } from "../api/client";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, InteractionType } from "../discord/types";
import { localizations, translate } from "../localization/catalog";
import { CommandInputError, OptionType, invokingUserId, normalizeTag, requireGuildId, stringOption } from "./command-utils";
import { modalFields, textField } from "./modals";
import type { Command, CommandContext, ComponentHandler } from "./types";

interface LinkResponse { account: { is_verified: boolean; tag: string } }
interface LinksResponse { items: Array<{ player_tag: string; is_verified: boolean }> }

export const linkCommand: Command = {
  ephemeral: true,
  definition: {
    contexts: [0], integration_types: [0], name: "link", type: 1,
    name_localizations: localizations("link.name"),
    description: translate("link.description"), description_localizations: localizations("link.description"),
  },
  async execute(context) { return linkModal(context); },
};

function linkModal(context: CommandContext) {
  requireGuildId(context);
  return { type: InteractionResponseType.Modal, data: {
    custom_id: "ck:link:submit", title: translate("link.title", context.locale),
    components: [
      { type: 10, content: translate("link.help", context.locale) },
      textField("player", translate("link.player", context.locale), 12),
      textField("api_token", translate("link.token", context.locale), 12),
    ],
  } };
}

const startLink: ComponentHandler = async (context) => {
  if (context.interaction.type !== InteractionType.MessageComponent) {
    throw new CommandInputError(translate("error.invalidInteraction", context.locale));
  }
  return linkModal(context);
};

const submitLink: ComponentHandler = async (context) => {
  requireGuildId(context);
  if (context.interaction.type !== InteractionType.ModalSubmit) {
    throw new CommandInputError(translate("error.invalidInteraction", context.locale));
  }
  const fields = modalFields(context.interaction.data?.components);
  const player = fields.get("player")?.value?.trim();
  const token = fields.get("api_token")?.value?.trim();
  if (!player || !token || player.length > 12 || token.length > 12) return retry(context, "link.required");
  let tag: string;
  try { tag = normalizeTag(player, context.locale); }
  catch { return retry(context, "error.tag"); }
  // Always use the signed interaction actor, never an option/modal recipient.
  const userId = invokingUserId(context);
  try {
    const existing = await context.services.api.get<LinksResponse>(`/v2/links/${userId}`);
    if (existing.items.some((item) => item.player_tag === tag && item.is_verified)) {
      return legacyMessage({ content: translate("link.already", context.locale, { tag }) }, { ephemeral: true });
    }
    // The canonical API verifies and atomically transfers other-owned links.
    // Do not automatically retry this mutation or persist its token.
    const result = await context.services.api.post<LinkResponse>(`/v2/links/${userId}`, { api_token: token, player_tag: tag });
    if (!result.account.is_verified || result.account.tag !== tag) return retry(context, "link.unavailable");
    return legacyMessage({ content: translate("link.success", context.locale, { tag }) }, { ephemeral: true });
  } catch (error) {
    if (error instanceof ClashKingApiError) {
      if (error.status === 403) return retry(context, "link.invalidToken");
      if (error.status === 404) return retry(context, "link.notFound");
      if (error.status === 409) return retry(context, "link.conflict");
    }
    return retry(context, "link.unavailable");
  }
};

function retry(context: CommandContext, key: Parameters<typeof translate>[0]) {
  return legacyMessage({ content: translate(key, context.locale), components: [actionRow({
    type: 2, style: 1, custom_id: "ck:link:start", label: translate("link.retry", context.locale),
  })] }, { ephemeral: true });
}

const linkHelp: ComponentHandler = async (context) => legacyMessage({ embeds: [{
  color: 0xed4245, title: translate("link.helpTitle", context.locale),
  description: `${translate("link.tagHelp", context.locale)}\n\n${translate("link.help", context.locale)}`,
  image: { url: "https://assets.clashk.ing/bot/images/api_token_help.png" },
}] }, { ephemeral: true });

export const linkComponentHandlers: Array<[string, ComponentHandler]> = [
  ["link:start", startLink], ["link:submit", submitLink], ["link:help", linkHelp],
];

export const unlinkCommand: Command = {
  deferred: true, ephemeral: true,
  definition: {
    contexts: [0], integration_types: [0], name: "unlink", type: 1,
    name_localizations: localizations("unlink.name"),
    description: translate("unlink.description"), description_localizations: localizations("unlink.description"),
    options: [{ name: "player", type: OptionType.String, required: true,
      name_localizations: localizations("player.name"),
      description: translate("player.description"), description_localizations: localizations("player.description") }],
  },
  async execute(context) {
    requireGuildId(context);
    const player = stringOption(context, "player");
    if (!player) throw new CommandInputError(translate("error.playerRequired", context.locale));
    const tag = normalizeTag(player, context.locale);
    try {
      await context.services.api.delete(`/v2/links/${invokingUserId(context)}/${encodeURIComponent(tag)}`);
    } catch (error) {
      if (error instanceof ClashKingApiError && [404, 409].includes(error.status)) {
        throw new CommandInputError(translate(error.status === 404 ? "unlink.notFound" : "unlink.conflict", context.locale));
      }
      throw error;
    }
    return legacyMessage({ content: translate("unlink.success", context.locale, { tag }) }, { ephemeral: true });
  },
};
