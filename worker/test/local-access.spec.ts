/// <reference types="@cloudflare/vitest-plugin/types" />
import { afterEach, describe, expect, it, vi } from "vitest";
import worker from "../src/index";
import type { Env } from "../src/env";
import { createExecutionContext } from "cloudflare:test";

afterEach(() => vi.unstubAllGlobals());
async function signed(type: number, actor?: string, base: Env["CLASHKING_API_BASE_URL"] = "http://127.0.0.1:8787") {
  const pair = await crypto.subtle.generateKey("Ed25519", true, ["sign", "verify"]);
  const hex = (bytes: ArrayBuffer) => [...new Uint8Array(bytes)].map(n => n.toString(16).padStart(2, "0")).join("");
  const body = JSON.stringify({ application_id: "app", type, guild_id: "guild", data: { name: "link" },
    ...(actor ? { member: { user: { id: actor }, roles: [] } } : {}) });
  const timestamp = "1789920000";
  const signature = hex(await crypto.subtle.sign("Ed25519", pair.privateKey, new TextEncoder().encode(timestamp + body)));
  const request = new Request("http://localhost/interactions", { method: "POST", body, headers: {
    "X-Signature-Ed25519": signature, "X-Signature-Timestamp": timestamp,
  } });
  const env = { APP_ENV: "dev", DASHBOARD_BASE_URL: "https://local-dash.clashk.ing", DISCORD_APPLICATION_ID: "app", DISCORD_PUBLIC_KEY: hex(await crypto.subtle.exportKey("raw", pair.publicKey)),
    CLASHKING_API_BASE_URL: base, LOCAL_TEST_USER_ID: "706149153431879760", DISCORD_BOT_TOKEN: "test", CLASHKING_API_TOKEN: "test" } satisfies Env;
  return { request, env };
}
describe("local-only interaction gate", () => {
  it.each([2, 3, 4, 5])("ignores other users for interaction type %i before service calls", async type => {
    const { request, env } = await signed(type, "other");
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const response = await worker.fetch(request, env, createExecutionContext());
    expect(response.status).toBe(204); expect(fetch).not.toHaveBeenCalled();
  });
  it("fails closed when the actor is missing", async () => {
    const { request, env } = await signed(2);
    expect((await worker.fetch(request, env, createExecutionContext())).status).toBe(204);
  });
  it("still answers Discord PING", async () => {
    const { request, env } = await signed(1);
    expect(await (await worker.fetch(request, env, createExecutionContext())).json()).toEqual({ type: 1 });
  });
  it("allows the test actor to open a modal", async () => {
    const { request, env } = await signed(2, "706149153431879760");
    expect(await (await worker.fetch(request, env, createExecutionContext())).json()).toMatchObject({ type: 9 });
  });
  it("allows other users to open a modal when the restriction is disabled", async () => {
    const { request, env } = await signed(2, "other");
    env.LOCAL_TEST_USER_ID = "";
    expect(await (await worker.fetch(request, env, createExecutionContext())).json()).toMatchObject({ type: 9 });
  });
  it("refuses a production API in restricted mode", async () => {
    const { request, env } = await signed(2, "706149153431879760", "https://api.clashk.ing");
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    expect((await worker.fetch(request, env, createExecutionContext())).status).toBe(503);
    expect(fetch).not.toHaveBeenCalled();
  });
});
