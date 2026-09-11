import commands from "../locales/en-US/commands.json";
import common from "../locales/en-US/common.json";
import responses from "../locales/en-US/responses.json";

const english = {
  ...commands,
  ...common,
  ...responses,
} as const;

export type LocaleKey = keyof typeof english;
export type LocaleVariables = Record<string, string | number>;

export const DEFAULT_LOCALE = "en-US";

export function resolveLocale(locale?: string, guildLocale?: string): string {
  if (locale?.toLowerCase().startsWith("en")) {
    return DEFAULT_LOCALE;
  }
  if (guildLocale?.toLowerCase().startsWith("en")) {
    return DEFAULT_LOCALE;
  }
  return DEFAULT_LOCALE;
}

export function translate(
  key: LocaleKey,
  _locale = DEFAULT_LOCALE,
  variables: LocaleVariables = {},
): string {
  return english[key].replace(/\{([A-Za-z]\w*)\}/g, (match, name: string) => {
    const value = variables[name];
    return value === undefined ? match : String(value);
  });
}
