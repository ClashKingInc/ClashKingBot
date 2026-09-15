import { describe, expect, it } from "vitest";

import { verifyDiscordRequest } from "../src/discord/signature";

describe("Discord request verification", () => {
  it("accepts a valid Ed25519 signature and rejects a changed body", async () => {
    const keyPair = await crypto.subtle.generateKey("Ed25519", true, ["sign", "verify"]);
    const publicKey = new Uint8Array(await crypto.subtle.exportKey("raw", keyPair.publicKey));
    const timestamp = "1788372000";
    const body = '{"type":1}';
    const signature = new Uint8Array(
      await crypto.subtle.sign(
        "Ed25519",
        keyPair.privateKey,
        new TextEncoder().encode(`${timestamp}${body}`),
      ),
    );

    await expect(
      verifyDiscordRequest(toHex(publicKey), toHex(signature), timestamp, body),
    ).resolves.toBe(true);
    await expect(
      verifyDiscordRequest(toHex(publicKey), toHex(signature), timestamp, `${body} `),
    ).resolves.toBe(false);
  });
});

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
