import { legacyMessage } from "../discord/components";
import { invokingUserId, OptionType } from "./command-utils";
import type { Command, CommandContext } from "./types";

interface Preferences { privateMode: boolean }
const path = (context: CommandContext) => `/v2/bot/users/${invokingUserId(context)}/preferences`;

export async function statsPrivateMode(context: CommandContext): Promise<boolean> {
  try {
    // Visibility is fixed by Discord at acknowledgement. Read it before the
    // defer, with a short timeout; unavailable preferences must fail private.
    const value = await context.services.api.get<Preferences>(path(context), {}, AbortSignal.timeout(1000));
    return value.privateMode !== false;
  } catch { return true; }
}

export const privacyCommand: Command = {
  deferred: true, ephemeral: true,
  definition: {
    name: "privacy", description: "View or change whether your /stats reports are private", type: 1,
    contexts: [0, 1, 2], integration_types: [0, 1],
    options: [{ name: "private_stats", description: "Only you can see your /stats reports", type: OptionType.Boolean }],
  },
  async execute(context) {
    const choice = context.options.get("private_stats")?.value;
    const value = choice === undefined
      ? await context.services.api.get<Preferences>(path(context))
      : await context.services.api.patch<Preferences>(path(context), { privateMode: choice });
    return legacyMessage({ content: value.privateMode
      ? "Your /stats reports are private. Only you can see them."
      : "Your /stats reports are public. People in the channel can see them.", allowed_mentions: { parse: [] } }, { ephemeral: true });
  },
};
