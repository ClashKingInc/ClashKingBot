import { describe, expect, it, vi } from "vitest";

import { commandDefinitions, dispatchInteraction } from "../src/commands/registry";
import type { CommandServices } from "../src/commands/types";
import type { DiscordInteraction } from "../src/discord/types";
import type { Env } from "../src/env";

const env = { APP_ENV: "dev" } as Env;

describe("first-slice command registry", () => {
  it("publishes only the implemented base and link command families", () => {
    expect(commandDefinitions.map((command) => command.name)).toEqual(["base", "link", "unlink"]);
    expect(commandDefinitions.find((command) => command.name === "base")?.options?.map((option) => option.name))
      .toEqual(["base_link", "description", "photo"]);
    expect(commandDefinitions.find((command) => command.name === "link")?.options?.map((option) => option.name))
      .toEqual(["player", "user", "api_token", "greet"]);
  });

  it("defers commands and completes the original interaction", async () => {
    const post = vi.fn(async () => ({ account: { is_verified: false, name: "Barbarian", tag: "#P0Y", townHallLevel: 1 }, message: "ok" }));
    const editOriginalInteractionResponse = vi.fn(async () => undefined);
    const pending: Promise<unknown>[] = [];
    const interaction = commandInteraction("link", [{ name: "player", type: 3, value: "P0Y" }]);
    const response = await dispatchInteraction(interaction, env, {
      api: { post }, discordRest: { editOriginalInteractionResponse },
    } as unknown as CommandServices, (promise) => pending.push(promise));

    expect(response).toMatchObject({ type: 5, data: { flags: 64 } });
    await pending[0];
    expect(post).toHaveBeenCalledWith("/v2/links/100000000000000001", { api_token: "", player_tag: "#P0Y" });
    expect(editOriginalInteractionResponse).toHaveBeenCalledOnce();
  });

  it("routes persistent link buttons to a modal", async () => {
    const interaction = commandInteraction("", []);
    interaction.type = 3;
    interaction.data = { custom_id: "ck:link:start" };
    const response = await dispatchInteraction(interaction, env, {
      api: { get: vi.fn(async () => ({ full_whitelist_role: null, require_api_token_when_linking: false })) },
    } as unknown as CommandServices);
    expect(response).toMatchObject({ type: 9, data: { custom_id: "ck:link:submit", title: "Link your account" } });
  });
});

function commandInteraction(name: string, options: NonNullable<DiscordInteraction["data"]>["options"]): DiscordInteraction {
  return {
    application_id: "app", data: { name, options }, guild_id: "200000000000000001", id: "interaction",
    member: { permissions: "32", roles: [], user: { id: "100000000000000001", username: "user" } },
    token: "token", type: 2, version: 1,
  };
}
