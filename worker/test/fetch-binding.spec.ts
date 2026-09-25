import { afterEach, describe, expect, it, vi } from "vitest";

import { ClashKingApiClient } from "../src/api/client";
import { DiscordRestClient } from "../src/discord/rest";

afterEach(() => vi.unstubAllGlobals());

describe("default platform fetch binding", () => {
  function installReceiverCheckedFetch() {
    const requests: string[] = [];
    vi.stubGlobal("fetch", function (this: unknown, input: RequestInfo | URL) {
      // Workerd rejects a platform fetch invoked with a client instance as `this`.
      if (this !== globalThis) throw new TypeError("Illegal invocation");
      requests.push(String(input));
      return Promise.resolve(Response.json({ ok: true }));
    });
    return requests;
  }

  it("uses the platform receiver for API requests without an injected fetch", async () => {
    const requests = installReceiverCheckedFetch();
    const client = new ClashKingApiClient({ baseUrl: "https://api.example", token: "test-token" });
    await expect(client.get("/v2/test")).resolves.toEqual({ ok: true });
    expect(requests).toEqual(["https://api.example/v2/test"]);
  });

  it("uses the platform receiver for Discord follow-ups and attachment downloads", async () => {
    const requests = installReceiverCheckedFetch();
    const client = new DiscordRestClient({ applicationId: "test-app", token: "test-token" });
    await expect(client.editOriginalInteractionResponse("interaction-token", { content: "Done" })).resolves.toBeUndefined();
    await expect(client.download("https://cdn.discordapp.com/test.png")).resolves.toBeInstanceOf(Blob);
    expect(requests).toEqual([
      "https://discord.com/api/v10/webhooks/test-app/interaction-token/messages/@original",
      "https://cdn.discordapp.com/test.png",
    ]);
  });
});
