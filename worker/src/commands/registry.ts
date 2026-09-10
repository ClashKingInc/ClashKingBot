import {
  InteractionResponseType,
  InteractionType,
  MessageFlags,
  type DiscordInteraction,
  type DiscordInteractionResponse,
  type InteractionOption,
} from "../discord/types";
import type { Env } from "../env";
import { resolveLocale, translate } from "../localization/catalog";
import { baseCommand, baseComponentHandlers } from "./base";
import { CommandInputError } from "./command-utils";
import { linkCommand, linkComponentHandlers, unlinkCommand } from "./link";
import type { Command, CommandContext, CommandServices, ComponentHandler } from "./types";

const commands: readonly Command[] = [baseCommand, linkCommand, unlinkCommand];
const commandByName = new Map(commands.map((command) => [command.definition.name, command]));
const componentHandlers = new Map<string, ComponentHandler>([
  ...baseComponentHandlers,
  ...linkComponentHandlers,
]);

export const commandDefinitions = commands.map((command) => command.definition);

export async function dispatchInteraction(
  interaction: DiscordInteraction,
  env: Env,
  services: CommandServices,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const context = createContext(interaction, env, services);
  if (interaction.type === InteractionType.ApplicationCommand) {
    return executeCommand(context, waitUntil);
  }
  if (interaction.type === InteractionType.MessageComponent || interaction.type === InteractionType.ModalSubmit) {
    return executePersistentHandler(context);
  }
  return unknownInteraction(context.locale);
}

function createContext(interaction: DiscordInteraction, env: Env, services: CommandServices): CommandContext {
  return {
    env,
    interaction,
    locale: resolveLocale(interaction.locale, interaction.guild_locale),
    options: flattenOptions(interaction.data?.options ?? []),
    path: [],
    services,
  };
}

async function executeCommand(
  context: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const name = context.interaction.data?.name;
  const command = name ? commandByName.get(name) : undefined;
  if (!command) {
    return unknownInteraction(context.locale);
  }
  if (!command.deferred || !waitUntil) {
    return command.execute(context);
  }
  waitUntil(command.execute(context).then(
    (response) => context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, response.data ?? {}),
    (error: unknown) => context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, {
      content: error instanceof CommandInputError ? error.message : translate("error.generic", context.locale),
      flags: MessageFlags.Ephemeral,
    }),
  ));
  return {
    data: command.ephemeral ? { flags: MessageFlags.Ephemeral } : {},
    type: InteractionResponseType.DeferredChannelMessageWithSource,
  };
}

async function executePersistentHandler(context: CommandContext): Promise<DiscordInteractionResponse> {
  const segments = context.interaction.data?.custom_id?.split(":") ?? [];
  if (segments.shift() !== "ck" || segments.length < 2) {
    return unknownInteraction(context.locale);
  }
  const domain = segments.shift();
  const action = segments.shift();
  const handler = domain && action ? componentHandlers.get(`${domain}:${action}`) : undefined;
  return handler ? handler(context, segments) : unknownInteraction(context.locale);
}

function unknownInteraction(locale: string): DiscordInteractionResponse {
  return {
    data: { content: translate("error.unknownCommand", locale), flags: MessageFlags.Ephemeral },
    type: InteractionResponseType.ChannelMessageWithSource,
  };
}

function flattenOptions(options: InteractionOption[]): ReadonlyMap<string, InteractionOption> {
  return new Map(options.map((option) => [option.name, option]));
}
