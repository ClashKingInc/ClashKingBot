import { describe, expect, it, vi } from "vitest";
import { dispatchInteraction } from "../src/commands/registry";
import type { CommandServices } from "../src/commands/types";
import type { DiscordInteraction } from "../src/discord/types";
import { DiscordRestClient } from "../src/discord/rest";
import type { Env } from "../src/env";

const env = {} as Env;
function input(ids = ["image"]): DiscordInteraction {
  return { application_id: "app", guild_id: "guild", channel_id: "channel", id: "interaction", token: "token", type: 5, version: 1,
    member: { roles: [], user: { id: "actor", username: "actor" } }, data: { custom_id: "base:submit", components: [
      { type: 18, component: { type: 4, custom_id: "base_link", value: "https://link.clashofclans.com/en?action=OpenLayout&id=TH17:test" } },
      { type: 18, component: { type: 4, custom_id: "description", value: "first\nsecond && third" } },
      { type: 18, component: { type: 19, custom_id: "screenshots", values: ids } },
    ], resolved: { attachments: { image: { id: "image", filename: "base.png", size: 5, content_type: "image/png", url: "https://cdn.discordapp.com/image.png", proxy_url: "" } } } },
  };
}
function mocks() {
  return { api: { postForm: vi.fn(async () => ({ url: "https://media.example/base.png" })),
    post: vi.fn(async () => ({ id: "42", messageId: "message", discordMessageUrl: "https://discord.com/channels/guild/channel/message" })) },
    discordRest: { download: vi.fn(async () => new Blob(["image"], { type: "image/png" })),
      editOriginalInteractionResponse: vi.fn(async () => undefined), editChannelMessage: vi.fn(async () => undefined) } };
}
describe("base modal", () => {
  it("opens without background work or slash options", async () => {
    const interaction = input(); interaction.type = 2; interaction.data = { name: "base" };
    const services = mocks(), wait = vi.fn();
    const result = await dispatchInteraction(interaction, env, services as unknown as CommandServices, wait);
    expect(result).toMatchObject({ type: 9, data: { custom_id: "base:submit" } });
    expect(wait).not.toHaveBeenCalled(); expect(services.api.post).not.toHaveBeenCalled();
  });
  it("defers modal submissions privately and preserves newlines and literal &&", async () => {
    const services = mocks(), pending: Promise<unknown>[] = [];
    const result = await dispatchInteraction(input(), env, services as unknown as CommandServices, promise => pending.push(promise));
    expect(result).toEqual({ type: 5, data: { flags: 64 } });
    await Promise.all(pending);
    expect(services.api.post).toHaveBeenCalledExactlyOnceWith("/v2/server/guild/bases", expect.objectContaining({ description: "first\nsecond && third" }));
    expect(services.discordRest.editOriginalInteractionResponse).toHaveBeenCalledWith("token", expect.objectContaining({ content: expect.stringContaining("Base posted") }));
  });
  it.each([[], ["image", "image"], ["missing"], ["1", "2", "3", "4", "5"]])("rejects invalid attachment references %j", async (...ids) => {
    const services = mocks();
    // Vitest expands each row; recover the attachment ID array from the row.
    await expect(dispatchInteraction(input(ids), env, services as unknown as CommandServices)).rejects.toThrow();
    expect(services.api.post).not.toHaveBeenCalled(); expect(services.discordRest.download).not.toHaveBeenCalled();
  });
  it.each(["image/svg+xml", "application/octet-stream"])("rejects unsupported attachment type %s", async contentType => {
    const interaction = input(), services = mocks();
    interaction.data!.resolved!.attachments!.image!.content_type = contentType;
    await expect(dispatchInteraction(interaction, env, services as unknown as CommandServices)).rejects.toThrow("PNG");
    expect(services.api.post).not.toHaveBeenCalled();
  });
  it("rejects oversized uploads before downloading", async () => {
    const interaction = input(), services = mocks();
    interaction.data!.resolved!.attachments!.image!.size = 25 * 1024 * 1024 + 1;
    await expect(dispatchInteraction(interaction, env, services as unknown as CommandServices)).rejects.toThrow("25 MiB");
    expect(services.discordRest.download).not.toHaveBeenCalled();
  });
  it("does not post a partial base when upload fails", async () => {
    const services = mocks(); services.api.postForm.mockRejectedValue(new Error("upload failed"));
    await expect(dispatchInteraction(input(), env, services as unknown as CommandServices)).rejects.toThrow("No base was posted");
    expect(services.api.post).not.toHaveBeenCalled();
  });
  it("uses guild language for shared controls and user language for the receipt", async () => {
    const interaction = input(), services = mocks(); interaction.locale = "es-ES"; interaction.guild_locale = "de";
    const result = await dispatchInteraction(interaction, env, services as unknown as CommandServices);
    expect(result.data?.content).toContain("Aldea publicada");
    expect(services.discordRest.editChannelMessage).toHaveBeenCalledWith("channel", "message", { components: [expect.objectContaining({
      components: [expect.objectContaining({ label: "Link abrufen" }), expect.anything(), expect.anything()],
    })] });
  });
  it("does not turn a translation edit failure into a second post", async () => {
    const interaction = input(), services = mocks(); interaction.locale = "en-US"; interaction.guild_locale = "fr";
    services.discordRest.editChannelMessage.mockRejectedValue(new Error("Discord unavailable"));
    const result = await dispatchInteraction(interaction, env, services as unknown as CommandServices);
    expect(result.data?.content).toContain("Base posted"); expect(services.api.post).toHaveBeenCalledOnce();
  });
});

describe("bounded attachment downloads", () => {
  it("rejects non-Discord URLs without fetching", async () => {
    const fetcher = vi.fn();
    const client = new DiscordRestClient({ applicationId: "app", token: "secret", fetch: fetcher });
    await expect(client.download("https://example.org/image.png")).rejects.toThrow("Untrusted");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("bounds streaming responses even without content-length", async () => {
    const client = new DiscordRestClient({ applicationId: "app", token: "secret", fetch: vi.fn(async () => new Response("oversized")) });
    await expect(client.download("https://cdn.discordapp.com/image.png", 4)).rejects.toThrow("size limit");
  });
  it("does not follow a CDN redirect to another host", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 302, headers: { location: "https://example.org" } }));
    const client = new DiscordRestClient({ applicationId: "app", token: "secret", fetch: fetcher });
    await expect(client.download("https://cdn.discordapp.com/image.png")).rejects.toThrow("302");
    expect(fetcher).toHaveBeenCalledExactlyOnceWith("https://cdn.discordapp.com/image.png", { redirect: "manual" });
  });
});
