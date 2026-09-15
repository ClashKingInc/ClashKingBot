import { describe, expect, it, vi } from "vitest";

import { baseCommand, baseComponentHandlers } from "../src/commands/base";
import type { CommandContext, CommandServices } from "../src/commands/types";
import type { Env } from "../src/env";

describe("base command family", () => {
  it("uploads the attachment, creates the base, and installs durable buttons", async () => {
    const postForm = vi.fn(async () => ({ filename: "base.png", url: "https://api.clashk.ing/v2/media/base.png" }));
    const post = vi.fn(async () => ({ baseLink: layoutLink, discordMessageUrl: "https://discord.com/channels/1/2/3", downloadCount: 0, downvotes: 0, id: "42", messageId: "3", upvotes: 0 }));
    const response = await baseCommand.execute(context({
      api: { post, postForm },
      discordRest: { download: vi.fn(async () => new Blob(["image"], { type: "image/png" })) },
    }));

    expect(postForm).toHaveBeenCalledOnce();
    expect(post).toHaveBeenCalledWith("/v2/server/1/bases", expect.objectContaining({ channelId: "2", images: ["https://api.clashk.ing/v2/media/base.png"] }));
    expect(response.data?.content).toContain("discord.com/channels/1/2/3");
  });

  it("preserves the order of all four supported images", async () => {
    const postForm = vi.fn(async (_path: string, form: FormData) => ({ filename: String(form.get("file")), url: `https://api.clashk.ing/v2/media/${postForm.mock.calls.length}.png` }));
    const post = vi.fn(async () => ({ baseLink: layoutLink, discordMessageUrl: "https://discord.com/channels/1/2/3", downloadCount: 0, downvotes: 0, id: "42", messageId: "3", upvotes: 0 }));
    await baseCommand.execute(context({ api: { post, postForm }, discordRest: {
      download: vi.fn(async () => new Blob(["image"], { type: "image/png" })),
    } }, true));
    expect(postForm).toHaveBeenCalledTimes(4);
    expect(post).toHaveBeenCalledWith("/v2/server/1/bases", expect.objectContaining({ images: [
      "https://api.clashk.ing/v2/media/1.png", "https://api.clashk.ing/v2/media/2.png",
      "https://api.clashk.ing/v2/media/3.png", "https://api.clashk.ing/v2/media/4.png",
    ] }));
  });

  it("keeps repeat downloads unique and returns the normalized layout link", async () => {
    const handler = new Map(baseComponentHandlers).get("base:link")!;
    const downloaders = new Set<string>();
    const postEmpty = vi.fn(async (path: string) => {
      downloaders.add(path.split("/").at(-1)!);
      return { downloadCount: downloaders.size };
    });
    const get = vi.fn(async () => boundBase());
    const services = { api: { get, postEmpty }, discordRest: {} };
    const response = await handler(context(services), ["42"]);
    await handler(context(services), ["42"]);
    expect(postEmpty).toHaveBeenNthCalledWith(2, "/v2/bases/42/downloaders/100000000000000001");
    expect(downloaders.size).toBe(1);
    expect(response.data?.content).toContain("action=OpenLayout&id=TH16%3Atest");
  });

  it.each([["base:upvote", "up"], ["base:downvote", "down"]] as const)("records and renders a %s", async (key, direction) => {
    const handler = new Map(baseComponentHandlers).get(key)!;
    const put = vi.fn(async () => ({ direction }));
    await handler(context({ api: { get: vi.fn(async () => boundBase()), put }, discordRest: {} }), ["42"]);
    expect(put).toHaveBeenCalledWith(`/v2/bases/42/votes/100000000000000001`, { direction });
  });

  it("switches one user's vote instead of retaining the opposite vote", async () => {
    const votes = new Map<string, "up" | "down">();
    const put = vi.fn(async (path: string, body: { direction: "up" | "down" }) => {
      votes.set(path.split("/").at(-1)!, body.direction);
      return body;
    });
    const services = { api: { get: vi.fn(async () => boundBase()), put }, discordRest: {} };
    await new Map(baseComponentHandlers).get("base:upvote")!(context(services), ["42"]);
    await new Map(baseComponentHandlers).get("base:downvote")!(context(services), ["42"]);
    expect([...votes.values()]).toEqual(["down"]);
  });
});

const layoutLink = "https://link.clashofclans.com/en?action=OpenLayout&id=TH16:test";

function boundBase() {
  return { baseLink: layoutLink, channelId: "2", description: "one\ntwo", id: "42", images: ["https://api.clashk.ing/v2/media/1.png"], messageId: "3", serverId: "1" };
}

function context(partial: Record<string, unknown>, fourImages = false): CommandContext {
  const attachments = Object.fromEntries(Array.from({ length: fourImages ? 4 : 1 }, (_, index) => {
    const suffix = index === 0 ? "" : `_${index + 1}`;
    return [`attachment${suffix}`, { content_type: "image/png", filename: `base${suffix}.png`, id: `attachment${suffix}`, proxy_url: "", size: 5, url: `https://cdn.discordapp.com/base${suffix}.png` }];
  }));
  const imageOptions = Array.from({ length: fourImages ? 4 : 1 }, (_, index) => {
    const suffix = index === 0 ? "" : `_${index + 1}`;
    return [`photo${suffix}`, { name: `photo${suffix}`, type: 11, value: `attachment${suffix}` }] as const;
  });
  return {
    env: {} as Env,
    interaction: {
      application_id: "app", channel_id: "2",
      data: { resolved: { attachments } },
      guild_id: "1", id: "interaction",
      message: { attachments: Object.values(attachments), channel_id: "2", content: "one\ntwo", id: "3" },
      member: { roles: [], user: { id: "100000000000000001", username: "user" } }, token: "token", type: 2, version: 1,
    },
    locale: "en-US",
    options: new Map([
      ["base_link", { name: "base_link", type: 3, value: layoutLink }],
      ["description", { name: "description", type: 3, value: "one&&two" }],
      ...imageOptions,
    ]),
    path: [], services: partial as unknown as CommandServices,
  };
}
