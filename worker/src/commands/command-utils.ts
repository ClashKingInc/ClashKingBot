import type { InteractionOption } from "../discord/types";
import type { CommandContext } from "./types";

export class CommandInputError extends Error {}

export const OptionType = {
  Subcommand: 1,
  SubcommandGroup: 2,
  String: 3,
  Integer: 4,
  Boolean: 5,
  User: 6,
  Channel: 7,
  Role: 8,
  Mentionable: 9,
  Number: 10,
  Attachment: 11,
} as const;

export function option(context: CommandContext, name: string): InteractionOption | undefined {
  return context.options.get(name);
}

export function stringOption(context: CommandContext, name: string): string | undefined {
  const value = option(context, name)?.value;
  return typeof value === "string" ? value.trim() : undefined;
}

export function invokingUserId(context: CommandContext): string {
  const id = context.interaction.member?.user?.id ?? context.interaction.user?.id;
  if (!id) throw new CommandInputError("Discord did not include an invoking user.");
  return id;
}

export function targetUserId(context: CommandContext, optionName = "user"): string {
  return stringOption(context, optionName) ?? invokingUserId(context);
}

export function requireGuildId(context: CommandContext): string {
  if (!context.interaction.guild_id) throw new CommandInputError("This command must be used in a server.");
  return context.interaction.guild_id;
}

export function normalizeTag(value: string): string {
  const compact = value.trim().toUpperCase().replace(/^#/, "").replace(/O/g, "0");
  if (!/^[0289PYLQGRJCUV]+$/.test(compact)) throw new CommandInputError("That is not a valid Clash tag.");
  return `#${compact}`;
}
