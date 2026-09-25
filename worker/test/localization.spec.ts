import { describe, expect, it } from "vitest";
import { baseCommand } from "../src/commands/base";
import { linkCommand } from "../src/commands/link";
import { commandDefinitions } from "../src/commands/registry";
import type { CommandContext } from "../src/commands/types";
import { SUPPORTED_LOCALES, localizations, resolveLocale, translate } from "../src/localization/catalog";

// Discord's supported locale list, checked against the official reference.
const expected = "id da de en-US es-ES es-419 fr hr it lt hu nl no pl pt-BR ro fi sv-SE vi tr cs el bg ru uk hi th zh-CN ja zh-TW ko".split(" ");
describe("localization coverage", () => {
  it("ships 31 catalogs with British English using en-US", () => expect([...SUPPORTED_LOCALES].sort()).toEqual(expected.sort()));
  it("resolves exact locales before guild fallback and preserves regional variants", () => {
    expect(resolveLocale("es-419", "de")).toBe("es-419");
    expect(resolveLocale("en-GB", "fr")).toBe("en-US");
    expect(translate("link.help", "en-GB")).toBe(translate("link.help", "en-US"));
    expect(resolveLocale("unknown", "ja")).toBe("ja");
    expect(resolveLocale("unknown")).toBe("en-US");
    expect(resolveLocale("PT-br")).toBe("pt-BR");
  });
  it.each(expected)("renders modal labels within Discord limits for %s", async locale => {
    const context = { locale, interaction: { guild_id: "guild" } } as CommandContext;
    for (const command of [baseCommand, linkCommand]) {
      const response = await command.execute(context);
      expect(response.type).toBe(9);
      expect(String(response.data?.title).length).toBeLessThanOrEqual(45);
      const components = response.data?.components as Array<{ type: number; label?: string; content?: string }>;
      expect(components.length).toBeLessThanOrEqual(5);
      for (const component of components) {
        if (component.label) expect(component.label.length).toBeLessThanOrEqual(45);
        if (component.content) expect(component.content.length).toBeLessThanOrEqual(4000);
      }
    }
    expect(translate("link.success", locale, { tag: "#P0Y" })).toContain("#P0Y");
    expect(translate("link.success", locale, { tag: "#P0Y" })).not.toContain("{tag}");
    expect(translate("base.getLink", locale).length).toBeLessThanOrEqual(80);
  });
  it("registers localized names and descriptions for every implemented command", () => {
    expect(Object.keys(localizations("link.description"))).toHaveLength(30);
    for (const command of commandDefinitions) {
      expect(Object.keys(command.name_localizations ?? {})).toHaveLength(30);
      expect(Object.keys(command.description_localizations ?? {})).toHaveLength(30);
    }
  });
});
