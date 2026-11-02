import { invokingUserId } from "./command-utils";
import type { CommandContext } from "./types";

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
