import { normalizeMessageControls } from "./discord/message-controls";
import { createServices } from "./services";
import { drainRefreshJobs } from "./refresh/runtime";
import { Effect } from "effect";
import { dispatchInteraction } from "./commands/registry";
import { giveawayEntry } from "./commands/giveaway";
import { ticketInteraction } from "./commands/ticket";
import { armyInteraction } from "./commands/army";
import { CommandInputError } from "./commands/command-utils";
import { verifyDiscordRequest } from "./discord/signature";
import {
  InteractionResponseType,
  InteractionType,
  type DiscordInteraction,
  type DiscordInteractionResponse,
} from "./discord/types";
import type { Env } from "./env";
import { resolveLocale, translate } from "./localization/catalog";
import { Services, runWithServices } from "./runtime";

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
} as const;

export default {
  async scheduled(_controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    if (env.LOCAL_TEST_USER_ID) return;
    const services = createServices(env);
    ctx.waitUntil((async () => {
      const started = Date.now();
      for (let batch = 0; batch < 10 && Date.now() - started < 45_000; batch++) {
        if (await drainRefreshJobs(services) === 0) break;
      }
    })());
  },
  async fetch(request: Request, env: Env, executionContext: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return Response.json({ environment: env.APP_ENV, ok: true });
    }

    if (request.method !== "POST" || url.pathname !== "/interactions") {
      return new Response("Not found", { status: 404 });
    }

    const body = await request.text();
    const verified = await verifyDiscordRequest(
      env.DISCORD_PUBLIC_KEY,
      request.headers.get("X-Signature-Ed25519"),
      request.headers.get("X-Signature-Timestamp"),
      body,
    );
    if (!verified) {
      return new Response("Invalid request signature", { status: 401 });
    }

    let interaction: DiscordInteraction;
    try {
      interaction = JSON.parse(body) as DiscordInteraction;
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    if (interaction.application_id !== env.DISCORD_APPLICATION_ID) {
      return new Response("Wrong application", { status: 401 });
    }
    if (interaction.type === InteractionType.Ping) {
      return json({ type: InteractionResponseType.Pong });
    }

    // No command, modal or component can reach services in a misconfigured local instance.
    const restrictedUser = env.LOCAL_TEST_USER_ID;
    if (restrictedUser) {
      const actor = interaction.member?.user?.id ?? interaction.user?.id;
      if (actor !== restrictedUser) return new Response(null, { status: 204 });
      const api = new URL(env.CLASHKING_API_BASE_URL);
      if (api.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(api.hostname)) {
        return new Response("Local testing requires a loopback API", { status: 503 });
      }
    }

    try {
      const response = await runWithServices(env, Effect.gen(function* () {
        const services = yield* Services;
        if (interaction.type !== InteractionType.ApplicationCommandAutocomplete &&
          (interaction.data?.name === "army" || interaction.data?.custom_id?.startsWith("ck:army:"))) {
          return yield* Effect.tryPromise({try:() => armyInteraction(interaction, { rawBody: body,
            timestamp: request.headers.get("X-Signature-Timestamp")!, signature: request.headers.get("X-Signature-Ed25519")! }, services,
            promise => executionContext.waitUntil(promise),env),catch:cause=>cause});
        }
        if (interaction.type !== InteractionType.ApplicationCommandAutocomplete &&
          (interaction.data?.name === "ticket" || interaction.data?.custom_id?.startsWith("ck:ticket:") || /^.{1,75}_(?:0|\d{10})$/u.test(interaction.data?.custom_id ?? ""))) {
          return yield* Effect.tryPromise({
            try: () => ticketInteraction(interaction, { rawBody: body,
              timestamp: request.headers.get("X-Signature-Timestamp")!, signature: request.headers.get("X-Signature-Ed25519")! }, services,
              promise => executionContext.waitUntil(promise)),
            catch: cause => cause,
          });
        }
        if (interaction.data?.custom_id?.startsWith("ck:giveaway:")) {
          return giveawayEntry(interaction, { rawBody: body,
            timestamp: request.headers.get("X-Signature-Timestamp")!, signature: request.headers.get("X-Signature-Ed25519")! },
            services, (promise) => executionContext.waitUntil(promise));
        }
        return yield* Effect.tryPromise({
          catch: (cause) => cause,
          try: () => dispatchInteraction(interaction, env, services, (promise) => executionContext.waitUntil(promise)),
        });
      }));
      return json(response.data ? { ...response, data: await normalizeMessageControls(response.data, createServices(env).discordRest) } : response);
    } catch (error) {
      console.error("Interaction handler failed", {
        command: interaction.data?.name,
        environment: env.APP_ENV,
        errorType: error instanceof Error ? error.name : "UnknownError",
        type: interaction.type,
      });
      return json({
        data: {
          content: error instanceof CommandInputError ? error.message : translate("error.generic", resolveLocale(interaction.locale, interaction.guild_locale)),
          flags: 1 << 6,
        },
        type: InteractionResponseType.ChannelMessageWithSource,
      });
    }
  },
} satisfies ExportedHandler<Env>;

function json(body: DiscordInteractionResponse): Response {
  return new Response(JSON.stringify(body), { headers: JSON_HEADERS });
}
