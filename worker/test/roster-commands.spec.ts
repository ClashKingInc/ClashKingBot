import { describe, expect, it, vi } from "vitest";
import { commandDefinitions, dispatchInteraction } from "../src/commands/registry";
import type { CommandServices } from "../src/commands/types";
import type { DiscordInteraction, DiscordInteractionResponse } from "../src/discord/types";
import type { Env } from "../src/env";

const id = "11111111-1111-4111-8111-111111111111";
const guild = "200000000000000001", actor = "706149153431879760", channel = "300000000000000001";
const env = { DISCORD_BOT_TOKEN: "test-only", DASHBOARD_BASE_URL: "https://local-dash.clashk.ing" } as Env;
function command(name: string, mode = "all"): DiscordInteraction {
  return { application_id: "app", id: "100000000000000001", token: "test", version: 1, type: 2,
    guild_id: guild, channel_id: channel, locale: "en-US", guild_locale: "en-US",
    member: { permissions: "32", roles: [], user: { id: actor, username: "tester" } },
    data: { name: "roster", options: [{ type: 1, name, options: name === "create" ? [] : [
      { type: 3, name: "roster", value: id }, { type: 3, name: "type", value: mode },
      { type: 3, name: "message", value: "Hello @everyone" },
    ] }] } };
}
function setup() {
  const roster = { id, serverId: guild, alias: "CWL", clanTag: "#CLAN", memberCount: 3, description: "",
    questionnaire: { questions: [] }, members: [
      { playerTag: "#P0Y", playerName: "One", townhall: 17, clanName: "Clan" },
      { playerTag: "#P2Y", playerName: "Two", townhall: 17, clanName: "Clan" },
      { playerTag: "#P8Y", playerName: "Unlinked", townhall: 17, clanName: "Clan" },
    ] };
  const get = vi.fn(async (path: string): Promise<unknown> => {
    if (path.endsWith("/clans-basic")) return [{ tag: "#CLAN" }];
    if (path.endsWith("/members")) return { members: [
      { tag: "#P0Y", name: "One", clan_tag: "#CLAN" }, { tag: "#P9Y", name: "Outside", clan_tag: "#CLAN" },
    ] };
    if (path.startsWith("/v2/links/server/")) return { filtered_members: 1, members: [
      { user_id: actor, linked_accounts: ["#P0Y", "#P2Y", "#P9Y"].map(player_tag => ({ player_tag })) },
    ] };
    if (path.endsWith("/rosters")) return { items: [roster] };
    return { roster };
  });
  const request = vi.fn(async () => ({ id: "900000000000000001" }));
  const services = { api: { get, post: vi.fn() }, discordRest: { request } } as unknown as CommandServices;
  return { roster, get, request, services };
}
function confirm(preview: DiscordInteractionResponse): DiscordInteraction {
  const components = preview.data?.components as Array<{ components: Array<{ custom_id: string }> }>;
  return { ...command("ping"), type: 3, data: { custom_id: components[0]!.components[0]!.custom_id },
    message: { id: "900000000000000001", content: String(preview.data?.content),
      embeds: preview.data?.embeds as Array<{ description?: string }> } };
}

describe("roster slash commands", () => {
  it("refreshes only the stored publication and acknowledges without a reply", async () => {
    const s = setup();
    const input = { ...command("post"), type: 3, data: { custom_id: `ck:roster:refresh:${id}` } };
    const result = await dispatchInteraction(input, env, s.services);
    expect(result).toEqual({ type: 6 });
    expect(s.services.api.post).toHaveBeenCalledExactlyOnceWith(`/v2/server/${guild}/rosters/${id}/refresh-publication`, {});
    expect(s.get).not.toHaveBeenCalled();
    expect(s.request).not.toHaveBeenCalled();
  });
  it("registers exactly post, ping, and create", () => {
    expect(commandDefinitions.find(c => c.name === "roster")?.options?.map(c => c.name)).toEqual(["post", "ping", "create"]);
  });
  it("links creation to the configured Dashboard without any writes", async () => {
    const s = setup();
    const result = await dispatchInteraction(command("create"), env, s.services);
    expect(JSON.stringify(result)).toContain(`https://local-dash.clashk.ing/dashboard/rosters?guildId=${guild}`);
    expect(result.data?.content).toBeUndefined();
    expect(result.data?.flags).toBe(64); expect(s.get).not.toHaveBeenCalled(); expect(s.request).not.toHaveBeenCalled();
  });
  it("fails closed without a Dashboard origin", async () => {
    const s = setup();
    const result = await dispatchInteraction(command("create"), {} as Env, s.services);
    expect(JSON.stringify(result)).not.toContain("https://dash.clashk.ing");
  });
  it("autocompletes server-scoped UUIDs and returns an autocomplete response", async () => {
    const s = setup(), input = command("post", "signup"); input.type = 4;
    input.data!.options![0]!.options![0] = { type: 3, name: "roster", focused: true, value: "cw" };
    expect(await dispatchInteraction(input, env, s.services)).toMatchObject({ type: 8, data: { choices: [{ name: "CWL | #CLAN | 👥 3", value: id }] } });
    s.roster.serverId = "other";
    expect(await dispatchInteraction(input, env, s.services)).toMatchObject({ type: 8, data: { choices: [] } });
  });
  it.each(["signup", "post", "static"])("posts %s with appropriate controls", async mode => {
    const s = setup(); await dispatchInteraction(command("post", mode), env, s.services);
    expect(s.services.api.post).toHaveBeenCalledExactlyOnceWith(`/v2/server/${guild}/rosters/${id}/post`,
      expect.objectContaining({ mode, dashboardUrl: expect.stringContaining(`rosterId=${id}`), leaveLabel: "Remove" }));
    expect(s.request).not.toHaveBeenCalled();
  });
  it("delegates one bounded static publication to the API", async () => {
    const s = setup(); s.roster.members = Array.from({ length: 60 }, (_, n) => ({ ...s.roster.members[0]!, playerName: `Player${n}` }));
    await dispatchInteraction(command("post", "static"), env, s.services);
    expect(s.services.api.post).toHaveBeenCalledTimes(1);
  });
  it.each(["post", "ping"])("checks management permission for %s", async name => {
    const s = setup(), input = command(name, name === "post" ? "signup" : "all"); input.member!.permissions = "0";
    expect((await dispatchInteraction(input, env, s.services)).data?.content).toContain("Manage Server");
    expect(s.get).not.toHaveBeenCalled(); expect(s.request).not.toHaveBeenCalled();
  });
});

describe("confirmed roster pings", () => {
  it.each(["missing", "outside", "all"])("previews %s privately and sends only after confirmation", async mode => {
    const s = setup(); const preview = await dispatchInteraction(command("ping", mode), env, s.services);
    expect(preview.data?.flags).toBe(64); expect(preview.data?.allowed_mentions).toEqual({ parse: [] });
    expect(s.request).not.toHaveBeenCalled();
    const input = confirm(preview);
    expect(input.data!.custom_id!.length).toBeLessThanOrEqual(100);
    await dispatchInteraction(input, env, s.services);
    const call = s.request.mock.calls[0] as unknown as [string, RequestInit];
    expect(call[0]).toBe(`/channels/${channel}/messages`);
    const body = JSON.parse(String(call[1].body));
    expect(body.allowed_mentions).toEqual({ parse: [], users: [actor] });
    expect(body.content.match(new RegExp(`<@${actor}>`, "g"))).toHaveLength(1);
    expect(body.content).toContain("Hello @everyone");
    expect(body.content.includes("Outside")).toBe(mode === "outside");
    expect(body.content.includes("One")).toBe(mode === "all");
  });
  it("rejects a changed target list", async () => {
    const s = setup(); const preview = await dispatchInteraction(command("ping"), env, s.services);
    s.roster.members.pop();
    expect((await dispatchInteraction(confirm(preview), env, s.services)).data?.content).toContain("expired or changed");
    expect(s.request).not.toHaveBeenCalled();
  });
  it.each(["actor", "channel", "message", "signature", "expired"])("rejects altered %s", async change => {
    const s = setup(), preview = await dispatchInteraction(command("ping"), env, s.services), input = confirm(preview);
    if (change === "actor") input.member!.user!.id = "500000000000000001";
    if (change === "channel") input.channel_id = "400000000000000001";
    if (change === "message") input.message!.embeds = [{ description: "changed" }];
    if (change === "signature") input.data!.custom_id = input.data!.custom_id!.slice(0, -24) + "0".repeat(24);
    if (change === "expired") { const parts = input.data!.custom_id!.split(":"); parts[5] = "1000000000"; input.data!.custom_id = parts.join(":"); }
    expect((await dispatchInteraction(input, env, s.services)).data?.content).toContain("expired or changed");
    expect(s.request).not.toHaveBeenCalled();
  });
  it("requires a configured server clan for clan-relative pings", async () => {
    const s = setup(); s.roster.clanTag = "#OTHER";
    expect((await dispatchInteraction(command("ping", "missing"), env, s.services)).data?.content).toContain("clan linked");
    expect(s.request).not.toHaveBeenCalled();
  });
});
