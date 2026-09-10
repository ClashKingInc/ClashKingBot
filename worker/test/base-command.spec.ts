import { describe, expect, it, vi } from "vitest";

import { baseCommand, baseComponentHandlers } from "../src/commands/base";
import type { CommandContext, CommandServices } from "../src/commands/types";
import type { Env } from "../src/env";

describe("base command family", () => {
  it("uploads the attachment, creates the base, and installs durable buttons", async () => {
    const postForm = vi.fn(async () => ({ filename: "base.png", url: "https://cdn.clashk.ing/base.png" }));
    const post = vi.fn(async () => ({ baseLink: layoutLink, discordMessageUrl: "https://discord.com/channels/1/2/3", downloadCount: 0, downloaders: [], id: "base-id", messageId: "3" }));
    const editChannelMessage = vi.fn(async () => undefined);
    const response = await baseCommand.execute(context({
      api: { post, postForm },
      discordRest: { download: vi.fn(async () => new Blob(["image"], { type: "image/png" })), editChannelMessage },
    }));

    expect(postForm).toHaveBeenCalledOnce();
    expect(post).toHaveBeenCalledWith("/v2/server/1/bases", expect.objectContaining({ channelId: "2", images: ["https://cdn.clashk.ing/base.png"] }));
    expect(editChannelMessage).toHaveBeenCalledWith("2", "3", { components: expect.any(Array) });
    expect(response.data?.content).toContain("discord.com/channels/1/2/3");
  });

  it("records a unique download and returns the normalized layout link", async () => {
    const handler = new Map(baseComponentHandlers).get("base:download")!;
    const postEmpty = vi.fn(async () => ({ downloadCount: 1 }));
    const get = vi.fn(async () => ({ baseLink: layoutLink, downloadCount: 1, downloaders: ["100000000000000001"], id: "base-id", messageId: "3" }));
    const response = await handler(context({ api: { get, postEmpty }, discordRest: { editChannelMessage: vi.fn(async () => undefined) } }), ["base-id"]);
    expect(postEmpty).toHaveBeenCalledWith("/v2/bases/base-id/downloaders/100000000000000001");
    expect(response.data?.content).toContain("action=OpenLayout&id=TH16%3Atest");
  });
});

const layoutLink = "https://link.clashofclans.com/en?action=OpenLayout&id=TH16:test";

function context(partial: Record<string, unknown>): CommandContext {
  return {
    env: {} as Env,
    interaction: {
      application_id: "app", channel_id: "2",
      data: { resolved: { attachments: { attachment: { content_type: "image/png", filename: "base.png", id: "attachment", proxy_url: "", size: 5, url: "https://cdn.discordapp.com/base.png" } } } },
      guild_id: "1", id: "interaction",
      member: { roles: [], user: { id: "100000000000000001", username: "user" } }, token: "token", type: 2, version: 1,
    },
    locale: "en-US",
    options: new Map([
      ["base_link", { name: "base_link", type: 3, value: layoutLink }],
      ["description", { name: "description", type: 3, value: "one&&two" }],
      ["photo", { name: "photo", type: 11, value: "attachment" }],
    ]),
    path: [], services: partial as unknown as CommandServices,
  };
}
