import { describe, expect, it, vi } from "vitest";

import { ClashKingApiClient } from "../src/api/client";

describe("ClashKingApiClient", () => {
  it("routes business reads and writes through the configured API with bot auth", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      Response.json({ ok: true }),
    );
    const client = new ClashKingApiClient({
      baseUrl: "https://api.example/",
      fetch: fetchMock as typeof fetch,
      token: "secret",
    });

    await client.get("/v2/test", { limit: 5 });
    await client.patch("v2/test", { enabled: true });
    await client.delete("/v2/test/1");

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("https://api.example/v2/test?limit=5");
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: "GET" });
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({ body: '{"enabled":true}', method: "PATCH" });
    expect(fetchMock.mock.calls[2]?.[1]).toMatchObject({ method: "DELETE" });
    const firstInit = fetchMock.mock.calls[0]![1]!;
    expect((firstInit.headers as Record<string, string>).Authorization).toBe("Bearer secret");
  });
});
