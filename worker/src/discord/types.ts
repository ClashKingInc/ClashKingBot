export const InteractionType = {
  Ping: 1,
  ApplicationCommand: 2,
  MessageComponent: 3,
  ApplicationCommandAutocomplete: 4,
  ModalSubmit: 5,
} as const;

export const InteractionResponseType = {
  Pong: 1,
  ChannelMessageWithSource: 4,
  DeferredChannelMessageWithSource: 5,
  DeferredUpdateMessage: 6,
  UpdateMessage: 7,
  ApplicationCommandAutocompleteResult: 8,
  Modal: 9,
} as const;

export const MessageFlags = {
  Ephemeral: 1 << 6,
  IsComponentsV2: 1 << 15,
} as const;

export interface InteractionOption {
  focused?: boolean;
  name: string;
  options?: InteractionOption[];
  type: number;
  value?: boolean | number | string;
}

export interface InteractionData {
  custom_id?: string;
  components?: ModalComponent[];
  name?: string;
  options?: InteractionOption[];
  resolved?: {
    attachments?: Record<string, DiscordAttachment>;
    channels?: Record<string, DiscordChannel>;
    members?: Record<string, DiscordMember>;
    users?: Record<string, DiscordUser>;
  };
  values?: string[];
}

export interface DiscordAttachment {
  content_type?: string;
  filename: string;
  id: string;
  proxy_url: string;
  size: number;
  url: string;
}

export interface ModalComponent {
  components?: ModalComponent[];
  custom_id?: string;
  type: number;
  value?: string;
}

export interface DiscordUser {
  avatar?: string | null;
  discriminator?: string;
  global_name?: string | null;
  id: string;
  username: string;
  [key: string]: unknown;
}

export interface DiscordMember {
  joined_at?: string;
  nick?: string | null;
  permissions?: string;
  roles: string[];
  user?: DiscordUser;
  [key: string]: unknown;
}

export interface DiscordGuild {
  id: string;
  name: string;
  [key: string]: unknown;
}

export interface DiscordChannel {
  guild_id?: string;
  id: string;
  name?: string;
  type: number;
  [key: string]: unknown;
}

export interface DiscordRole {
  id: string;
  name: string;
  [key: string]: unknown;
}

export interface DiscordInteraction {
  application_id: string;
  channel_id?: string;
  data?: InteractionData;
  guild_id?: string;
  guild_locale?: string;
  id: string;
  locale?: string;
  message?: DiscordMessage;
  member?: DiscordMember;
  token: string;
  type: number;
  user?: DiscordUser;
  version: number;
}

export interface DiscordInteractionResponse {
  data?: Record<string, unknown>;
  type: number;
}

export interface DiscordApplicationEmoji {
  animated?: boolean;
  available?: boolean;
  id: string;
  managed?: boolean;
  name: string;
}

export interface DiscordMessage {
  attachments?: DiscordAttachment[];
  channel_id?: string;
  content?: string;
  embeds?: Array<{ description?: string; [key: string]: unknown }>;
  id: string;
  [key: string]: unknown;
}
