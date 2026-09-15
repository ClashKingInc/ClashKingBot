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
      .toEqual(["base_link", "description", "photo", "photo_2", "photo_3", "photo_4"]);
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

  it("routes the exact unprefixed bigint base component IDs", async () => {
    const interaction = commandInteraction("", []);
    interaction.type = 3;
    interaction.data = { custom_id: "base:upvote:42" };
    interaction.channel_id = "300000000000000001";
    interaction.message = { attachments: [], channel_id: interaction.channel_id, content: "description", id: "400000000000000001" };
    const get = vi.fn(async () => ({ baseLink: "https://link.clashofclans.com/en?action=OpenLayout&id=TH17%3Atest",
      channelId: interaction.channel_id, description: "description", id: "42", images: [], messageId: interaction.message?.id,
      serverId: interaction.guild_id }));
    const put = vi.fn(async () => ({ direction: "up" }));
    const response = await dispatchInteraction(interaction, env, {
      api: { get, put }, discordRest: {},
    } as unknown as CommandServices);
    expect(get).toHaveBeenCalledWith("/v2/bases/legacy/400000000000000001");
    expect(put).toHaveBeenCalledWith("/v2/bases/42/votes/100000000000000001", { direction: "up" });
    expect(response).toMatchObject({ type: 4, data: { content: "Upvote recorded.", flags: 64 } });
  });

  it.each(["ck:base:upvote:42", "base:upvote:42:extra"])("rejects noncanonical base component ID %s", async (customId) => {
    const interaction = commandInteraction("", []);
    interaction.type = 3;
    interaction.data = { custom_id: customId };
    const put = vi.fn();
    const response = await dispatchInteraction(interaction, env, { api: { put }, discordRest: {} } as unknown as CommandServices);
    expect(put).not.toHaveBeenCalled();
    expect(response).toMatchObject({ type: 4, data: { content: "That command is not available yet." } });
  });
});

function commandInteraction(name: string, options: NonNullable<DiscordInteraction["data"]>["options"]): DiscordInteraction {
  return {
    application_id: "app", data: { name, options }, guild_id: "200000000000000001", id: "interaction",
    member: { permissions: "32", roles: [], user: { id: "100000000000000001", username: "user" } },
    token: "token", type: 2, version: 1,
  };
}
