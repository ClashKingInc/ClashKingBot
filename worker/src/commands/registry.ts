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
    return executePersistentHandler(context, waitUntil);
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

async function executePersistentHandler(
  context: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const customId = context.interaction.data?.custom_id ?? "";
  if (customId === "link" || customId === "who") {
    const handler = componentHandlers.get("base:legacy");
    if (!handler) return unknownInteraction(context.locale);
    return waitUntil ? deferPersistentHandler(context, handler, [customId], waitUntil) : handler(context, [customId]);
  }
  const segments = customId.split(":");
  const prefix = segments.shift();
  const domain = prefix === "ck" ? segments.shift() : prefix;
  const action = segments.shift();
  if (!domain || !action || (prefix === "ck" ? domain !== "link" : domain !== "base")) return unknownInteraction(context.locale);
  if (domain === "base" && segments.length !== 1) return unknownInteraction(context.locale);
  const handler = domain && action ? componentHandlers.get(`${domain}:${action}`) : undefined;
  if (!handler) return unknownInteraction(context.locale);
  return domain === "base" && waitUntil
    ? deferPersistentHandler(context, handler, segments, waitUntil)
    : handler(context, segments);
}

function deferPersistentHandler(
  context: CommandContext,
  handler: ComponentHandler,
  segments: string[],
  waitUntil: (promise: Promise<unknown>) => void,
): DiscordInteractionResponse {
  waitUntil(completeDeferredInteraction(context, handler(context, segments)));
  return { data: { flags: MessageFlags.Ephemeral }, type: InteractionResponseType.DeferredChannelMessageWithSource };
}

async function completeDeferredInteraction(context: CommandContext, pending: Promise<DiscordInteractionResponse>): Promise<void> {
  try {
    const response = await pending;
    await context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, response.data ?? {});
  } catch (error) {
    await context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, {
      content: error instanceof CommandInputError ? error.message : translate("error.generic", context.locale),
      flags: MessageFlags.Ephemeral,
    });
  }
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
