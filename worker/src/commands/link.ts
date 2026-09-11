import { legacyMessage } from "../discord/components";
import { ClashKingApiError } from "../api/client";
import { InteractionResponseType, type ModalComponent } from "../discord/types";
import {
  CommandInputError,
  OptionType,
  invokingUserId,
  normalizeTag,
  requireGuildId,
  stringOption,
  targetUserId,
} from "./command-utils";
import type { Command, CommandContext, ComponentHandler } from "./types";

interface LinkResponse {
  account: { is_verified: boolean; name: string; tag: string; townHallLevel: number };
  message: string;
}

const playerOption = {
  description: "Player tag as found in game",
  name: "player",
  required: true,
  type: OptionType.String,
} as const;

export const linkCommand: Command = {
  deferred: true,
  ephemeral: true,
  definition: {
    contexts: [0],
    description: "Link Clash of Clans accounts to your Discord profile",
    integration_types: [0],
    name: "link",
    options: [
      playerOption,
      { description: "Discord member; defaults to you", name: "user", required: false, type: OptionType.User },
      { description: "Player API token", max_length: 12, name: "api_token", required: false, type: OptionType.String },
      { choices: [{ name: "Yes", value: "Yes" }, { name: "No", value: "No" }], description: "Send the configured clan greeting", name: "greet", required: false, type: OptionType.String },
    ],
    type: 1,
  },
  async execute(context) {
    const userId = targetUserId(context);
    const privileged = await canManageLinks(context);
    if (userId !== invokingUserId(context) && !privileged) {
      throw new CommandInputError("Manage Server permission or a configured full-whitelist role is required to link another member.");
    }
    if (!privileged && !stringOption(context, "api_token") && (await serverLinkSettings(context)).require_api_token_when_linking) {
      throw new CommandInputError("This server requires the player API token from Clash of Clans Settings > More Settings.");
    }
    return linkAccount(context, requiredString(context, "player"), stringOption(context, "api_token"), userId);
  },
};

export const unlinkCommand: Command = {
  deferred: true,
  ephemeral: true,
  definition: {
    contexts: [0],
    description: "Unlink a Clash account from Discord",
    integration_types: [0],
    name: "unlink",
    options: [playerOption],
    type: 1,
  },
  async execute(context) {
    const tag = normalizeTag(requiredString(context, "player"));
    const response = await context.services.api.delete<{ message: string }>(
      `/v2/links/${invokingUserId(context)}/${encodeURIComponent(tag)}`,
    );
    return legacyMessage({ embeds: [{
      color: 0x57f287,
      description: `[${tag}](${playerLink(tag)}) has been unlinked from discord.`,
      title: response.message,
    }] }, { ephemeral: true });
  },
};

const startLink: ComponentHandler = async (context) => {
  const settings = await serverLinkSettings(context);
  const tokenRequired = settings.require_api_token_when_linking && !hasLinkPrivilege(context, settings);
  return { data: {
    components: [
      modalRow("player", "Player Tag", true, 12),
      modalRow("api_token", tokenRequired ? "API Token" : "(Optional) API Token", tokenRequired, 12),
    ],
    custom_id: "ck:link:submit",
    title: "Link your account",
  },
  type: InteractionResponseType.Modal };
};

const submitLink: ComponentHandler = async (context) => {
  const values = modalValues(context.interaction.data?.components ?? []);
  const player = values.get("player");
  if (!player) throw new CommandInputError("A player tag is required.");
  const privileged = await canManageLinks(context);
  if (!privileged && !values.get("api_token") && (await serverLinkSettings(context)).require_api_token_when_linking) {
    throw new CommandInputError("This server requires the player API token from Clash of Clans Settings > More Settings.");
  }
  return linkAccount(context, player, values.get("api_token"), invokingUserId(context));
};

const linkHelp: ComponentHandler = async () => legacyMessage({ embeds: [
  {
    color: 0xed4245,
    description: "Open the game, navigate to your profile, then use the copy icon near the top-left. Make sure you copied the player tag rather than the clan tag.",
    title: "Finding a player tag",
  },
  {
    color: 0xed4245,
    description: "Open Clash of Clans and navigate to Settings > More Settings, or [open More Settings](https://link.clashofclans.com/?action=OpenMoreSettings), then copy the API token at the bottom.",
    title: "What is your API token?",
  },
] }, { ephemeral: true });

export const linkComponentHandlers: Array<[string, ComponentHandler]> = [
  ["link:start", startLink], ["link:submit", submitLink], ["link:help", linkHelp],
];

async function linkAccount(context: CommandContext, rawTag: string, apiToken: string | undefined, userId: string) {
  const tag = normalizeTag(rawTag);
  try {
    const result = await context.services.api.post<LinkResponse>(`/v2/links/${userId}`, {
      api_token: apiToken ?? "",
      player_tag: tag,
    });
    return legacyMessage({ embeds: [{
      color: 0xf2a900,
      description: `[${result.account.name}](${playerLink(result.account.tag)}) linked to <@${userId}>`,
      title: "Link Complete",
    }] }, { ephemeral: true });
  } catch (error) {
    if (error instanceof ClashKingApiError && error.status === 409) {
      throw new CommandInputError("This account is linked to someone else. Add the API token from Clash of Clans settings to prove ownership.");
    }
    if (error instanceof ClashKingApiError && error.status === 403) {
      throw new CommandInputError("The API token is invalid. Check Clash of Clans Settings > More Settings and try again.");
    }
    if (error instanceof ClashKingApiError && error.status === 404) {
      throw new CommandInputError(`Sorry, ${tag} is not a valid player tag.`);
    }
    throw error;
  }
}

function modalRow(customId: string, label: string, required: boolean, maxLength: number) {
  return { components: [{ custom_id: customId, label, max_length: maxLength, required, style: 1, type: 4 }], type: 1 };
}

function modalValues(components: ModalComponent[]): Map<string, string> {
  const result = new Map<string, string>();
  const visit = (items: ModalComponent[]): void => {
    for (const item of items) {
      if (item.custom_id && item.value !== undefined) result.set(item.custom_id, item.value.trim());
      if (item.components) visit(item.components);
    }
  };
  visit(components);
  return result;
}

function playerLink(tag: string): string {
  return `https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=${encodeURIComponent(tag)}`;
}

function requiredString(context: CommandContext, name: string): string {
  const value = stringOption(context, name);
  if (!value) throw new CommandInputError(`Missing required option ${name}.`);
  return value;
}

interface LinkSettings {
  full_whitelist_role: string | null;
  require_api_token_when_linking: boolean;
}

async function serverLinkSettings(context: CommandContext): Promise<LinkSettings> {
  return context.services.api.get<LinkSettings>(`/v2/server/${requireGuildId(context)}/settings`);
}

async function canManageLinks(context: CommandContext): Promise<boolean> {
  if (hasManageGuild(context)) return true;
  return hasLinkPrivilege(context, await serverLinkSettings(context));
}

function hasLinkPrivilege(context: CommandContext, settings: LinkSettings): boolean {
  if (hasManageGuild(context)) return true;
  const role = settings.full_whitelist_role;
  return role !== null && context.interaction.member?.roles.includes(role) === true;
}

function hasManageGuild(context: CommandContext): boolean {
  const raw = context.interaction.member?.permissions;
  if (raw) {
    const permissions = BigInt(raw);
    if ((permissions & ((1n << 3n) | (1n << 5n))) !== 0n) return true;
  }
  return false;
}
