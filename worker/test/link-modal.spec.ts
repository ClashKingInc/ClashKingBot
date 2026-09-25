import { describe, expect, it, vi } from "vitest";
import { ClashKingApiError } from "../src/api/client";
import { dispatchInteraction } from "../src/commands/registry";
import type { CommandServices } from "../src/commands/types";
import type { DiscordInteraction } from "../src/discord/types";
import type { Env } from "../src/env";

const env = {} as Env;
function interaction(token = "valid-token", legacy = false): DiscordInteraction {
  const fields = [
    { type: 4, custom_id: "player", value: "p0y" },
    { type: 4, custom_id: "api_token", value: token },
    { type: 4, custom_id: "user", value: "someone-else" },
  ];
  return { application_id: "app", guild_id: "guild", id: "interaction", token: "interaction-token", type: 5, version: 1,
    member: { permissions: "8", roles: ["old-whitelist"], user: { id: "actor", username: "actor" } },
    data: { custom_id: "ck:link:submit", components: legacy ? [{ type: 1, components: fields }]
      : fields.map(component => ({ type: 18, component })) },
  };
}
function services(items: Array<{ player_tag: string; is_verified: boolean }> = []) {
  return { api: { get: vi.fn(async () => ({ items })), post: vi.fn(async () => ({ account: { tag: "#P0Y", is_verified: true } })) },
    discordRest: { editOriginalInteractionResponse: vi.fn(async () => undefined) } };
}
describe("self-only verified linking", () => {
  it("opens a required-token modal without API calls or deferral", async () => {
    const input = interaction(); input.type = 2; input.data = { name: "link", options: [{ name: "user", type: 6, value: "other" }] };
    const mocks = services(), pending = vi.fn();
    const result = await dispatchInteraction(input, env, mocks as unknown as CommandServices, pending);
    expect(result).toMatchObject({ type: 9, data: { custom_id: "ck:link:submit", components: [
      { type: 10, content: expect.stringContaining("Illustrated guide") },
      { type: 18, component: { custom_id: "player", required: true } },
      { type: 18, component: { custom_id: "api_token", required: true } },
    ] } });
    expect(mocks.api.get).not.toHaveBeenCalled(); expect(pending).not.toHaveBeenCalled();
    expect(JSON.stringify(result)).toContain("API token is one time use & used to verify that the account is yours.");
    expect(JSON.stringify(result)).not.toContain("moves an account");
  });
  it.each([false, true])("always targets the actor and sends the token (legacy rows: %s)", async (legacy) => {
    const mocks = services();
    const result = await dispatchInteraction(interaction("valid-token", legacy), env, mocks as unknown as CommandServices);
    expect(mocks.api.get).toHaveBeenCalledWith("/v2/links/actor");
    expect(mocks.api.post).toHaveBeenCalledExactlyOnceWith("/v2/links/actor", { player_tag: "#P0Y", api_token: "valid-token" });
    expect(result).toMatchObject({ type: 4, data: { flags: 64, content: expect.stringContaining("Ownership verified") } });
    expect(JSON.stringify(result)).not.toContain("valid-token");
  });
  it.each(["", "   ", "too-long-token-value"])("never lets administrators omit or bypass token validation: %j", async token => {
    const mocks = services();
    const result = await dispatchInteraction(interaction(token), env, mocks as unknown as CommandServices);
    expect(mocks.api.post).not.toHaveBeenCalled(); expect(mocks.api.get).not.toHaveBeenCalled();
    expect(result.data?.components).toEqual([expect.objectContaining({ components: [expect.objectContaining({ custom_id: "ck:link:start" })] })]);
  });
  it("reports an already-verified self link without rewriting it", async () => {
    const mocks = services([{ player_tag: "#P0Y", is_verified: true }]);
    const result = await dispatchInteraction(interaction(), env, mocks as unknown as CommandServices);
    expect(result.data?.content).toContain("already linked"); expect(mocks.api.post).not.toHaveBeenCalled();
  });
  it("verifies an existing unverified self link", async () => {
    const mocks = services([{ player_tag: "#P0Y", is_verified: false }]);
    await dispatchInteraction(interaction(), env, mocks as unknown as CommandServices);
    expect(mocks.api.post).toHaveBeenCalledOnce();
  });
  it.each([[403, "does not match"], [404, "No player"], [409, "could not be linked"], [503, "temporarily unavailable"]])("localizes API failure %i without reflecting backend data", async (status, text) => {
    const mocks = services(); mocks.api.post.mockRejectedValue(new ClashKingApiError(Number(status), "sensitive-backend-text"));
    const result = await dispatchInteraction(interaction(), env, mocks as unknown as CommandServices);
    expect(result.data?.content).toContain(text); expect(JSON.stringify(result)).not.toContain("sensitive-backend-text");
  });
  it("rejects a submit ID sent as a button, before mutation", async () => {
    const mocks = services(), input = interaction(); input.type = 3;
    const result = await dispatchInteraction(input, env, mocks as unknown as CommandServices);
    expect(result.type).toBe(4); expect(mocks.api.post).not.toHaveBeenCalled();
  });
  it("does not claim success for an unverified API result", async () => {
    const mocks = services(); mocks.api.post.mockResolvedValue({ account: { tag: "#P0Y", is_verified: false } });
    const result = await dispatchInteraction(interaction(), env, mocks as unknown as CommandServices);
    expect(result.data?.content).toContain("temporarily unavailable");
  });
  it("uses the invoking user's locale", async () => {
    const mocks = services(), input = interaction(""); input.locale = "es-ES"; input.guild_locale = "de";
    const result = await dispatchInteraction(input, env, mocks as unknown as CommandServices);
    expect(result.data?.content).toBe("Introduce tu etiqueta de jugador y tu token de API.");
  });
});
