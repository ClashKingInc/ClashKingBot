import type { ClashKingApiClient } from "../api/client";
import type { DiscordRestClient } from "../discord/rest";
import type { DiscordInteraction, DiscordInteractionResponse, InteractionOption } from "../discord/types";
import type { Env } from "../env";

export interface ApplicationCommandDefinition {
  contexts?: Array<0 | 1 | 2>;
  description: string;
  description_localizations?: Record<string, string>;
  integration_types?: Array<0 | 1>;
  name: string;
  name_localizations?: Record<string, string>;
  options?: ApplicationCommandOption[];
  type: 1 | 2 | 3;
}

export interface ApplicationCommandOption {
  autocomplete?: boolean;
  choices?: Array<{ name: string; value: string | number }>;
  description: string;
  max_length?: number;
  max_value?: number;
  min_length?: number;
  min_value?: number;
  name: string;
  options?: ApplicationCommandOption[];
  required?: boolean;
  type: number;
}

export interface CommandServices {
  api: ClashKingApiClient;
  discordRest: DiscordRestClient;
}

export interface CommandContext {
  env: Env;
  interaction: DiscordInteraction;
  locale: string;
  options: ReadonlyMap<string, InteractionOption>;
  path: readonly string[];
  services: CommandServices;
}

export interface AutocompleteChoice {
  name: string;
  value: string | number;
}

export interface Command {
  autocomplete?(context: CommandContext): Promise<AutocompleteChoice[]>;
  deferred?: boolean;
  definition: ApplicationCommandDefinition;
  ephemeral?: boolean;
  execute(context: CommandContext): Promise<DiscordInteractionResponse>;
}

export type ComponentHandler = (
  context: CommandContext,
  segments: string[],
) => Promise<DiscordInteractionResponse>;
