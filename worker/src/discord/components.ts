import { MessageFlags, type DiscordInteractionResponse } from "./types";

export const ComponentType = {
  ActionRow: 1,
  Button: 2,
  StringSelect: 3,
  UserSelect: 5,
  RoleSelect: 6,
  MentionableSelect: 7,
  ChannelSelect: 8,
  Section: 9,
  TextDisplay: 10,
  Thumbnail: 11,
  MediaGallery: 12,
  File: 13,
  Separator: 14,
  Container: 17,
} as const;

export interface ComponentEmoji {
  animated?: boolean;
  id?: string | null;
  name?: string | null;
}

export interface ButtonComponent {
  custom_id?: string;
  disabled?: boolean;
  emoji?: ComponentEmoji;
  label?: string;
  style: 1 | 2 | 3 | 4 | 5;
  type: 2;
  url?: string;
}

export interface StringSelectOption {
  default?: boolean;
  description?: string;
  emoji?: ComponentEmoji;
  label: string;
  value: string;
}

interface SelectComponentBase {
  custom_id: string;
  disabled?: boolean;
  max_values?: number;
  min_values?: number;
  placeholder?: string;
}

export interface StringSelectComponent extends SelectComponentBase {
  options: StringSelectOption[];
  type: 3;
}

export interface UserSelectComponent extends SelectComponentBase {
  type: 5;
}

export interface RoleSelectComponent extends SelectComponentBase {
  type: 6;
}

export interface MentionableSelectComponent extends SelectComponentBase {
  type: 7;
}

export interface ChannelSelectComponent extends SelectComponentBase {
  channel_types?: number[];
  type: 8;
}

export type SelectComponent =
  | ChannelSelectComponent
  | MentionableSelectComponent
  | RoleSelectComponent
  | StringSelectComponent
  | UserSelectComponent;

export interface TextDisplayComponent {
  content: string;
  type: 10;
}

export interface ThumbnailComponent {
  description?: string;
  media: { url: string };
  spoiler?: boolean;
  type: 11;
}

export interface SectionComponent {
  accessory?: ButtonComponent | ThumbnailComponent;
  components: TextDisplayComponent[];
  type: 9;
}

export interface SeparatorComponent {
  divider?: boolean;
  spacing?: 1 | 2;
  type: 14;
}

export interface MediaGalleryComponent {
  items: Array<{
    description?: string;
    media: { url: string };
    spoiler?: boolean;
  }>;
  type: 12;
}

export interface FileComponent {
  file: {
    content_type?: string;
    proxy_url?: string;
    url: string;
  };
  name?: string;
  spoiler?: boolean;
  type: 13;
}

export interface ActionRowComponent {
  components: Array<ButtonComponent | SelectComponent>;
  type: 1;
}

export type ContainerChild =
  | ActionRowComponent
  | FileComponent
  | MediaGalleryComponent
  | SelectComponent
  | SectionComponent
  | SeparatorComponent
  | TextDisplayComponent;

export interface ContainerComponent {
  accent_color?: number | null;
  components: ContainerChild[];
  spoiler?: boolean;
  type: 17;
}

export type V2Component = ContainerComponent | ContainerChild;

export interface LegacyEmbed {
  color?: number;
  description?: string;
  footer?: { icon_url?: string; text: string };
  title?: string;
  url?: string;
}

export function linkButton(label: string, url: string, emoji?: ComponentEmoji): ButtonComponent {
  return {
    ...(emoji ? { emoji } : {}),
    label,
    style: 5,
    type: ComponentType.Button,
    url,
  };
}

export function actionRow(...components: Array<ButtonComponent | SelectComponent>): ActionRowComponent {
  return { components, type: ComponentType.ActionRow };
}

export function componentsV2(
  components: V2Component[],
  options: { ephemeral?: boolean } = {},
): DiscordInteractionResponse {
  if (components.length === 0) {
    throw new Error("Components V2 responses require at least one component");
  }
  return {
    data: {
      components,
      flags: MessageFlags.IsComponentsV2 | (options.ephemeral ? MessageFlags.Ephemeral : 0),
    },
    type: 4,
  };
}

export function legacyMessage(
  data: {
    components?: ActionRowComponent[];
    content?: string;
    embeds?: LegacyEmbed[];
  },
  options: { ephemeral?: boolean } = {},
): DiscordInteractionResponse {
  return {
    data: {
      ...data,
      ...(options.ephemeral ? { flags: MessageFlags.Ephemeral } : {}),
    },
    type: 4,
  };
}
