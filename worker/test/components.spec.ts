import { describe, expect, it } from "vitest";

import { ComponentType, componentsV2, legacyMessage } from "../src/discord/components";
import { MessageFlags } from "../src/discord/types";

describe("Discord response builders", () => {
  it("marks Components V2 messages without legacy content", () => {
    const response = componentsV2(
      [{ content: "Hello", type: ComponentType.TextDisplay }],
      { ephemeral: true },
    );

    expect(response.data).toEqual({
      components: [{ content: "Hello", type: 10 }],
      flags: MessageFlags.IsComponentsV2 | MessageFlags.Ephemeral,
    });
    expect(response.data).not.toHaveProperty("content");
    expect(response.data).not.toHaveProperty("embeds");
  });

  it("keeps legacy responses free of the Components V2 flag", () => {
    const response = legacyMessage({ content: "Hello" }, { ephemeral: true });
    expect(response.data?.flags).toBe(MessageFlags.Ephemeral);
  });
});
