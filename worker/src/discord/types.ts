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

export type Snowflake = string;

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
    attachments?: Record<Snowflake, DiscordAttachment>;
    channels?: Record<Snowflake, DiscordChannel>;
    members?: Record<Snowflake, DiscordMember>;
    users?: Record<Snowflake, DiscordUser>;
  };
  values?: string[];
}

export interface DiscordAttachment {
  content_type?: string;
  filename: string;
  id: Snowflake;
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
  id: Snowflake;
  username: string;
  [key: string]: unknown;
}

export interface DiscordMember {
  joined_at?: string;
  nick?: string | null;
  permissions?: string;
  roles: Snowflake[];
  user?: DiscordUser;
  [key: string]: unknown;
}

export interface DiscordGuild {
  id: Snowflake;
  name: string;
  [key: string]: unknown;
}

export interface DiscordChannel {
  guild_id?: Snowflake;
  id: Snowflake;
  name?: string;
  type: number;
  [key: string]: unknown;
}

export interface DiscordRole {
  id: Snowflake;
  name: string;
  [key: string]: unknown;
}

export interface DiscordInteraction {
  application_id: Snowflake;
  channel_id?: Snowflake;
  data?: InteractionData;
  guild_id?: Snowflake;
  guild_locale?: string;
  id: Snowflake;
  locale?: string;
  message?: { id: Snowflake; [key: string]: unknown };
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
  id: Snowflake;
  managed?: boolean;
  name: string;
}
