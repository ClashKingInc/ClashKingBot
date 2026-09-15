import { describe, expect, it, vi } from "vitest";

import { CommandInputError } from "../src/commands/command-utils";
import { dispatchInteraction } from "../src/commands/registry";
import type { CommandServices } from "../src/commands/types";
import type { DiscordInteraction } from "../src/discord/types";
import type { Env } from "../src/env";

const guildId = "200000000000000001";
const channelId = "300000000000000001";
const messageId = "400000000000000001";
const userId = "100000000000000001";
const baseLink = "https://link.clashofclans.com/en?action=OpenLayout&id=TH17%3Atest";
const env = { APP_ENV: "dev" } as Env;

describe("legacy base first-click conversion", () => {
  it("defers an old link click and performs the required conversion order", async () => {
    const fixture = legacyFixture();
    const pending: Promise<unknown>[] = [];
    const response = await dispatchInteraction(legacyInteraction("link", "Message description"), env, fixture.services, (promise) => pending.push(promise));

    expect(response).toEqual({ data: { flags: 64 }, type: 5 });
    await pending[0];
    expect(fixture.events).toEqual(["resolve", "stage:1", "edit", "finalize", "download", "callback"]);
    expect(fixture.editChannelMessage).toHaveBeenCalledWith(channelId, messageId, { components: [{ components: [
      { custom_id: "base:link:42", label: "Open Layout", style: 1, type: 2 },
      { custom_id: "base:upvote:42", label: "Upvote", style: 2, type: 2 },
      { custom_id: "base:downvote:42", label: "Downvote", style: 2, type: 2 },
    ], type: 1 }] });
    expect(fixture.finalizeBodies).toEqual([{ channelId, description: "Message description", serverId: guildId }]);
    expect(fixture.callbackBodies[0]).toMatchObject({ content: expect.stringContaining("action=OpenLayout"), flags: 64 });
  });

  it("routes old who and uses the embed-description fallback", async () => {
    const fixture = legacyFixture({ downloaders: [userId] });
    const response = await dispatchInteraction(legacyInteraction("who", "", "Embed description"), env, fixture.services);

    expect(fixture.events).toEqual(["resolve", "stage:1", "edit", "finalize", "get"]);
    expect(fixture.finalizeBodies).toEqual([{ channelId, description: "Embed description", serverId: guildId }]);
    expect(response.data?.embeds).toEqual([expect.objectContaining({ description: `➼ <@${userId}>` })]);
  });

  it("does not finalize or record the click when the Discord edit fails", async () => {
    const fixture = legacyFixture({ failedEdits: 1 });
    await expect(dispatchInteraction(legacyInteraction("link", "Description"), env, fixture.services))
      .rejects.toEqual(expect.objectContaining<Partial<CommandInputError>>({ message: expect.stringContaining("remains unconverted") }));

    expect(fixture.staged.size).toBe(1);
    expect(fixture.finalizeBodies).toHaveLength(0);
    expect(fixture.downloaders.size).toBe(0);
    expect(fixture.bound).toBe(false);
  });

  it("retries after a partial failure without copying an already-staged image twice", async () => {
    const fixture = legacyFixture({ failedEdits: 1 });
    const interaction = legacyInteraction("link", "Description");
    await expect(dispatchInteraction(interaction, env, fixture.services)).rejects.toBeInstanceOf(CommandInputError);
    const response = await dispatchInteraction(interaction, env, fixture.services);

    expect(fixture.stageRequests).toBe(2);
    expect(fixture.mediaCopies).toBe(1);
    expect(fixture.finalizeBodies).toHaveLength(1);
    expect(fixture.downloaders).toEqual(new Set([userId]));
    expect(response.data?.content).toContain("action=OpenLayout");
  });

  it("stops before Discord and finalization when the media copy fails", async () => {
    const fixture = legacyFixture({ failedStages: 1 });
    await expect(dispatchInteraction(legacyInteraction("link", "Description"), env, fixture.services))
      .rejects.toEqual(expect.objectContaining<Partial<CommandInputError>>({ message: expect.stringContaining("could not be copied") }));
    expect(fixture.editChannelMessage).not.toHaveBeenCalled();
    expect(fixture.finalizeBodies).toHaveLength(0);
    expect(fixture.bound).toBe(false);
  });

  it("finishes finalization from a new button after the post-edit finalize call fails", async () => {
    const fixture = legacyFixture({ failedFinalizes: 1 });
    await expect(dispatchInteraction(legacyInteraction("link", "Description"), env, fixture.services))
      .rejects.toEqual(expect.objectContaining<Partial<CommandInputError>>({ message: expect.stringContaining("new buttons") }));

    const pending: Promise<unknown>[] = [];
    const response = await dispatchInteraction(
      legacyInteraction("base:link:42", "Description"), env, fixture.services, (promise) => pending.push(promise),
    );
    expect(response).toEqual({ data: { flags: 64 }, type: 5 });
    await pending[0];
    expect(fixture.events).toEqual([
      "resolve", "stage:1", "edit", "finalize",
      "resolve", "stage:1", "edit", "finalize", "download", "callback",
    ]);
    expect(fixture.mediaCopies).toBe(1);
    expect(fixture.finalizeBodies).toHaveLength(2);
    expect(fixture.bound).toBe(true);
    expect(fixture.callbackBodies.at(-1)?.content).toContain("action=OpenLayout");
  });
});

function legacyInteraction(customId: string, content: string, embedDescription?: string): DiscordInteraction {
  return {
    application_id: "app", channel_id: channelId, data: { custom_id: customId }, guild_id: guildId, id: "interaction",
    member: { roles: [], user: { id: userId, username: "user" } },
    message: {
      attachments: [{ content_type: "image/png", filename: "base.png", id: "attachment", proxy_url: "", size: 5, url: "https://cdn.discordapp.com/attachments/1/base.png" }],
      channel_id: channelId, content, embeds: embedDescription === undefined ? [] : [{ description: embedDescription }], id: messageId,
    },
    token: "token", type: 3, version: 1,
  };
}

function legacyFixture(options: { downloaders?: string[]; failedEdits?: number; failedFinalizes?: number; failedStages?: number } = {}) {
  const events: string[] = [];
  const staged = new Map<number, string>();
  const downloaders = new Set(options.downloaders ?? []);
  const finalizeBodies: unknown[] = [];
  const callbackBodies: Array<Record<string, unknown>> = [];
  let bound = false;
  let description = "Imported description";
  let editFailures = options.failedEdits ?? 0;
  let finalizeFailures = options.failedFinalizes ?? 0;
  let stageFailures = options.failedStages ?? 0;
  let stageRequests = 0;
  let mediaCopies = 0;

  const get = vi.fn(async (path: string) => {
    if (path === `/v2/bases/legacy/${messageId}`) {
      events.push("resolve");
      return { baseLink, channelId: bound ? channelId : null, description, id: "42", images: [...staged.values()], messageId, serverId: bound ? guildId : null };
    }
    events.push("get");
    return { baseLink, channelId, createdAt: "2026-09-11T00:00:00Z", description, discordMessageUrl: "https://discord.com/channels/1/2/3",
      downloadCount: downloaders.size, downloaders: [...downloaders], downvotes: 0, id: "42", images: [...staged.values()], messageId, serverId: guildId, upvotes: 0 };
  });
  const post = vi.fn(async (path: string, body: Record<string, unknown>) => {
    if (path.includes("/images/")) {
      const position = Number(path.split("/").at(-1));
      events.push(`stage:${position}`);
      stageRequests += 1;
      if (stageFailures > 0) {
        stageFailures -= 1;
        throw new Error("copy failed");
      }
      if (!staged.has(position)) {
        mediaCopies += 1;
        staged.set(position, `https://api.clashk.ing/v2/media/base-${position}.png`);
      }
      return { baseId: "42", imageUrl: staged.get(position), position };
    }
    events.push("finalize");
    finalizeBodies.push(body);
    if (finalizeFailures > 0) {
      finalizeFailures -= 1;
      throw new Error("finalize failed");
    }
    bound = true;
    description = String(body.description ?? "");
    return { baseId: "42", channelId, serverId: guildId };
  });
  const postEmpty = vi.fn(async (path: string) => {
    events.push("download");
    downloaders.add(path.split("/").at(-1)!);
    return { baseId: "42", downloadCount: downloaders.size, userId };
  });
  const editChannelMessage = vi.fn(async () => {
    events.push("edit");
    if (editFailures > 0) {
      editFailures -= 1;
      throw new Error("edit failed");
    }
  });
  const editOriginalInteractionResponse = vi.fn(async (_token: string, body: Record<string, unknown>) => {
    events.push("callback");
    callbackBodies.push(body);
  });
  const services = { api: { get, post, postEmpty }, discordRest: { editChannelMessage, editOriginalInteractionResponse } } as unknown as CommandServices;
  return {
    callbackBodies, downloaders, editChannelMessage, events, finalizeBodies, get bound() { return bound; },
    get mediaCopies() { return mediaCopies; }, services, staged, get stageRequests() { return stageRequests; },
  };
}
