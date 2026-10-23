import { ClashKingApiClient } from "./api/client";
import type { CommandServices } from "./commands/types";
import { DiscordRestClient } from "./discord/rest";
import type { Env } from "./env";

export function createServices(env: Env): CommandServices {
  const rest = new DiscordRestClient({
    applicationId: env.DISCORD_APPLICATION_ID,
    token: env.DISCORD_BOT_TOKEN,
  });
  return {
    api: new ClashKingApiClient({
      baseUrl: env.CLASHKING_API_BASE_URL,
      token: env.CLASHKING_API_TOKEN,
    }),
    discordRest: rest,
  };
}
