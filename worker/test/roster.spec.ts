import { describe, expect, it, vi } from "vitest";
import { ClashKingApiError } from "../src/api/client";
import { dispatchInteraction } from "../src/commands/registry";
import type { CommandServices } from "../src/commands/types";
import type { DiscordInteraction } from "../src/discord/types";
import type { Env } from "../src/env";
import { SUPPORTED_LOCALES } from "../src/localization/catalog";

const id = "11111111-1111-4111-8111-111111111111";
const guild = "200000000000000001";
const actor = "706149153431879760";
const env = { DASHBOARD_BASE_URL: "https://local-dash.clashk.ing", DISCORD_BOT_TOKEN: "test-only" } as Env;
function roster() {
  return { id, serverId: guild, alias: "War roster", description: "Hello @everyone", memberCount: 1,
    questionnaire: { questions: [] as Array<{ id: string; label: string; type: string; required: boolean; options: string[]; order: number }> },
    members: [{ playerTag: "#P0Y", playerName: "Player", townhall: 17, clanName: "Clan" }] };
}
function setup() {
  const data = roster();
  const get = vi.fn(async (path: string) => path.startsWith("/v2/links/")
    ? { items: [{ player_tag: "#P0Y", is_verified: true }] }
    : path.endsWith("/accounts") ? { items: [{ tag: "#P0Y", name: "Player", townhall: 17, isVerified: true, signedUp: false }] }
    : path.endsWith("/rosters") ? { items: [data] } : { roster: data });
  const post = vi.fn(async (_path: string, _body: unknown) => ({ roster_id: id }));
  const request = vi.fn(async (_path: string, _init: RequestInit) => ({ id: "message" }));
  const editOriginalInteractionResponse = vi.fn(async () => undefined);
  const services = { api: { get, post }, discordRest: { request, editOriginalInteractionResponse, listApplicationEmojis: vi.fn(async () => [{ id: "123", name: "th18" }]) } } as unknown as CommandServices;
  return { data, get, post, request, services, editOriginalInteractionResponse };
}
function interaction(customId?: string, type = 3, permissions = "32"): DiscordInteraction {
  return { application_id: "app", id: "interaction", token: "token", version: 1, type: customId ? type : 2,
    guild_id: guild, channel_id: "300000000000000001", locale: "en-US",
    member: { permissions, roles: [], user: { id: actor, username: "Tester" } },
    data: customId ? { custom_id: `ck:roster:${customId}` } : { name: "roster" } };
}
describe("roster flows", () => {
  it("caps multi-account selection by available capacity and submits an atomic batch", async () => {
    const s = setup(), original = s.get.getMockImplementation()!;
    s.get.mockImplementation(async path => path.endsWith("/accounts") ? { remainingSlots: 2, items: ["#P0Y", "#P0Q", "#P0L"].map(tag => ({ tag, name: tag, townhall: 18, isVerified: false, signedUp: false })) } : original(path));
    const modal = await dispatchInteraction(interaction(`join:${id}`), env, s.services);
    expect(modal).toMatchObject({ type: 9, data: { components: [{ component: { max_values: 2 } }] } });
    const input = interaction(String(modal.data?.custom_id).replace("ck:roster:", ""), 5);
    input.data!.components = [{ type: 18, component: { type: 3, custom_id: "player", values: ["#P0Y", "#P0Q"] } }];
    await dispatchInteraction(input, env, s.services);
    expect(s.post).toHaveBeenCalledExactlyOnceWith(`/v2/server/${guild}/rosters/${id}/submissions/batch`, { playerTags: ["#P0Y", "#P0Q"], discordUserId: actor });
  });
  it("uses owned account dropdowns, paging beyond 25 choices", async () => {
    const s = setup(); const original = s.get.getMockImplementation()!;
    s.get.mockImplementation(async path => path.endsWith("/accounts") ? { items: Array.from({ length: 26 }, (_, n) => ({
      tag: `#P${n}`, name: `Account ${n}`, townhall: 18, isVerified: false, signedUp: false,
    })) } : original(path));
    const pages = await dispatchInteraction(interaction(`join:${id}`), env, s.services);
    expect(pages.type).toBe(4);
    const input = interaction(`join-page:${id}`); input.data!.values = ["1"];
    const modal = await dispatchInteraction(input, env, s.services);
    expect(modal).toMatchObject({ type: 9, data: { components: [{ component: { type: 3, options: [{ value: "#P25", emoji: { id: "123", name: "th18" } }] } }] } });
  });
  it("lets an unverified owned account withdraw and supplies the signed actor", async () => {
    const s = setup(); const original = s.get.getMockImplementation()!;
    s.get.mockImplementation(async path => path.endsWith("/accounts") ? { items: [{ tag: "#P0Y", name: "Player", townhall: 18, isVerified: false, signedUp: true }] } : original(path));
    const modal = await dispatchInteraction(interaction(`leave:${id}`), env, s.services);
    expect(modal.type).toBe(9);
    const input = interaction(`withdraw:${id}`, 5);
    input.data!.components = [{ type: 18, component: { type: 3, custom_id: "player", values: ["#P0Y"] } }];
    await dispatchInteraction(input, env, s.services);
    expect(s.post).toHaveBeenCalledWith(`/v2/server/${guild}/rosters/${id}/withdraw`, { playerTag: "#P0Y", discordUserId: actor });
  });
  it("browses privately with a picker and no slash options", async () => {
    const s = setup();
    expect(await dispatchInteraction(interaction("list:0"), env, s.services)).toMatchObject({ type: 4, data: {
      flags: 64, components: [{ components: [{ type: 3, options: [{ value: id }] }] }, { components: [{ label: "Create roster" }] }],
    } });
    expect(s.get).toHaveBeenCalledWith(`/v2/server/${guild}/rosters`, {}, expect.any(AbortSignal));
  });
  it("defers the roster browser and completes its original response", async () => {
    const s = setup(), pending: Promise<unknown>[] = [];
    expect(await dispatchInteraction(interaction(), env, s.services, p => pending.push(p))).toMatchObject({ type: 5 });
    await Promise.all(pending);
    expect(s.editOriginalInteractionResponse).toHaveBeenCalledOnce();
  });
  it("shows every roster over multiple bounded picker pages", async () => {
    const s = setup();
    s.get.mockResolvedValue({ items: Array.from({ length: 32 }, (_, i) => ({ ...s.data, alias: `Roster ${String(i).padStart(2, "0")}` })) });
    const pages = await Promise.all([0, 1, 2].map(p => dispatchInteraction(interaction(`list:${p}`), env, s.services)));
    const values = pages.map(p => (p.data!.components as Array<{ components: Array<{ options: unknown[] }> }>)[0]!.components[0]!.options.length);
    expect(values).toEqual([15, 15, 2]);
  });
  it("opens the Dashboard privately without an API read", async () => {
    const s = setup(), wait = vi.fn();
    const result = await dispatchInteraction(interaction("create"), env, s.services, wait);
    expect(result).toMatchObject({ type: 4, data: { flags: 64, components: [{ components: [{ url: `https://local-dash.clashk.ing/dashboard/rosters?guildId=${guild}` }] }] } });
    expect(s.get).not.toHaveBeenCalled(); expect(wait).not.toHaveBeenCalled();
  });
  it.each([`post:${id}`])("denies management action %s to nonmanagers", async action => {
    const s = setup();
    const result = await dispatchInteraction(interaction(action, action === "save" ? 5 : 3, "0"), env, s.services);
    expect(result.data?.content).toContain("Manage Server");
    expect(s.get).not.toHaveBeenCalled(); expect(s.post).not.toHaveBeenCalled(); expect(s.request).not.toHaveBeenCalled();
  });
  it("rejects stale creation modals without creating a roster", async () => {
    const s = setup(), input = interaction("save", 5);
    input.data!.components = [
      { type: 4, custom_id: "alias", value: " War " }, { type: 4, custom_id: "clan", value: "poy" },
      { type: 4, custom_id: "description", value: "line1\nline2" },
    ];
    await dispatchInteraction(input, env, s.services);
    expect(s.post).not.toHaveBeenCalled();
  });
  it("renders bounded messages and disables mentions", async () => {
    const s = setup(); s.data.alias = "a".repeat(100); s.data.description = "@everyone ".repeat(100);
    s.data.members = Array.from({ length: 55 }, () => ({ ...s.data.members[0]!, playerName: "a".repeat(100), clanName: "b".repeat(100) }));
    const result = await dispatchInteraction(interaction(`view:${id}:2`), env, s.services);
    expect(String(result.data?.content).length).toBeLessThanOrEqual(2000);
    expect(result.data?.allowed_mentions).toEqual({ parse: [] });
    expect(result.data?.content).toContain("¹⁷"); expect(result.data?.content).toContain("3/4");
  });
  it("rejects mismatched server data", async () => {
    const s = setup(); s.data.serverId = "another-server";
    const result = await dispatchInteraction(interaction(`view:${id}`), env, s.services);
    expect(result.data?.content).not.toContain("War roster");
  });
  it.each([`view:${id}:extra`, `join:${id}:extra`, `submit:${id}`, "save:extra", "post:../other", `view:${id}:-1`])("rejects malformed ID %s", async customId => {
    const s = setup(); await dispatchInteraction(interaction(customId), env, s.services);
    expect(s.get).not.toHaveBeenCalled(); expect(s.post).not.toHaveBeenCalled();
  });
  it("rejects buttons masquerading as modal submissions", async () => {
    const s = setup(); await dispatchInteraction(interaction("save", 3), env, s.services);
    expect(s.post).not.toHaveBeenCalled();
  });
  it("posts a standalone snapshot with nonce deduplication", async () => {
    const s = setup(); await dispatchInteraction(interaction(`post:${id}`), env, s.services);
    const body = s.post.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(body).toMatchObject({ mode: "signup", nonce: "interaction", dashboardUrl: expect.stringContaining(`rosterId=${id}`), leaveLabel: "Remove" });
    expect(s.request).not.toHaveBeenCalled();
  });
  it("localizes shared posts for the guild and private acknowledgements for the actor", async () => {
    const s = setup(); const input = interaction(`post:${id}`); input.locale = "fr"; input.guild_locale = "de";
    const result = await dispatchInteraction(input, env, s.services);
    const body = s.post.mock.calls[0]?.[1] as Record<string, unknown>;
    expect(body.viewLabel).toBe("Kader ansehen");
    expect(result.data?.content).toBe("Effectif publié.");
  });
  it("submits typed answers and the signed actor, never an input recipient", async () => {
    const s = setup(); s.data.questionnaire.questions = [
      { id: "ready", label: "Ready?", type: "boolean", required: true, options: [], order: 0 },
      { id: "time", label: "Time?", type: "single_select", required: true, options: ["Morning", "Night"], order: 1 },
      { id: "note", label: "Note", type: "text", required: false, options: [], order: 2 },
    ];
    const modal = await dispatchInteraction(interaction(`join:${id}`), env, s.services);
    const input = interaction(String(modal.data?.custom_id).replace("ck:roster:", ""), 5);
    expect(modal.data?.components).toEqual(expect.arrayContaining([expect.objectContaining({ label: "Accounts", component: expect.objectContaining({ max_values: 1 }) })]));
    input.data!.components = [{ type: 18, component: { type: 3, custom_id: "player", values: ["#P0Y"] } },
      { type: 18, component: { type: 3, custom_id: "q0", values: ["false"] } },
      { type: 18, component: { type: 3, custom_id: "q1", values: ["1"] } },
      { type: 18, component: { type: 4, custom_id: "q2", value: "first\nsecond" } }];
    await dispatchInteraction(input, env, s.services);
    expect(s.post).toHaveBeenCalledExactlyOnceWith(`/v2/server/${guild}/rosters/${id}/submissions`, {
      playerTag: "#P0Y", discordUserId: actor, answers: { ready: false, time: "Night", note: "first\nsecond" },
    });
  });
  it("rejects changed questionnaires instead of reassigning answers", async () => {
    const s = setup(); const modal = await dispatchInteraction(interaction(`join:${id}`), env, s.services);
    s.data.questionnaire.questions.push({ id: "new", label: "New?", type: "text", required: true, options: [], order: 0 });
    await dispatchInteraction(interaction(String(modal.data?.custom_id).replace("ck:roster:", ""), 5), env, s.services);
    expect(s.post).not.toHaveBeenCalled();
  });
  it("does not silently drop oversized questionnaires", async () => {
    const s = setup(); s.data.questionnaire.questions = Array.from({ length: 5 }, (_, i) => ({ id: `${i}`, label: "Question", type: "text", required: true, options: [], order: i }));
    const result = await dispatchInteraction(interaction(`join:${id}`), env, s.services);
    expect(result.type).toBe(4); expect(result.data?.content).toContain("cannot fit");
  });
  it("requires a verified self account before submitting", async () => {
    const s = setup(); const modal = await dispatchInteraction(interaction(`join:${id}`), env, s.services);
    s.get.mockImplementation(async path => path.startsWith("/v2/links/") ? { items: [{ player_tag: "#P0Y", is_verified: false }] } : { roster: { ...s.data, requireVerified: true } });
    const input = interaction(String(modal.data?.custom_id).replace("ck:roster:", ""), 5);
    input.data!.components = [{ type: 4, custom_id: "player", value: "#P0Y" }];
    expect((await dispatchInteraction(input, env, s.services)).data?.content).toContain("/link");
    expect(s.post).not.toHaveBeenCalled();
  });
  it("does not expose API error bodies or automatically retry writes", async () => {
    const s = setup(); s.post.mockRejectedValue(new ClashKingApiError(500, "secret"));
    const input = interaction("save", 5); input.data!.components = [{ type: 4, custom_id: "alias", value: "War" }, { type: 4, custom_id: "clan", value: "#P0Y" }];
    const result = await dispatchInteraction(input, env, s.services);
    expect(s.post).not.toHaveBeenCalled(); expect(JSON.stringify(result)).not.toContain("secret");
  });
  it.each(SUPPORTED_LOCALES)("fits localized modal labels for %s", async locale => {
    const s = setup(); const input = interaction("create"); input.locale = locale;
    const result = await dispatchInteraction(input, env, s.services);
    expect(String(result.data?.title).length).toBeLessThanOrEqual(45);
    expect(result.type).toBe(4);
  });
});
