import { readdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const localeRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "locales");
const namespaces = ["commands", "common", "responses"] as const;
const localeNames = (await readdir(localeRoot, { withFileTypes: true }))
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort(compareText);

const english = await readLocale("en-US");
const englishKeys = Object.keys(english).sort(compareText);
const errors: string[] = [];

for (const locale of localeNames) {
  const catalog = await readLocale(locale);
  const keys = Object.keys(catalog).sort(compareText);
  for (const missing of englishKeys.filter((key) => !keys.includes(key))) {
    errors.push(`${locale}: missing ${missing}`);
  }
  for (const unknown of keys.filter((key) => !englishKeys.includes(key))) {
    errors.push(`${locale}: unknown ${unknown}`);
  }
  for (const key of englishKeys) {
    if (catalog[key] && placeholders(catalog[key]) !== placeholders(english[key])) {
      errors.push(`${locale}: placeholders differ for ${key}`);
    }
  }
}

if (errors.length > 0) {
  throw new Error(`Locale validation failed:\n${errors.join("\n")}`);
}

console.log(`Validated ${localeNames.length} locale(s) and ${englishKeys.length} keys`);

async function readLocale(locale: string): Promise<Record<string, string>> {
  const result: Record<string, string> = {};
  for (const namespace of namespaces) {
    const path = join(localeRoot, locale, `${namespace}.json`);
    const parsed = JSON.parse(await readFile(path, "utf8")) as Record<string, unknown>;
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value !== "string") {
        throw new TypeError(`${locale}/${namespace}.json: ${key} must be a string`);
      }
      const namespacedKey = `${namespace}:${key}`;
      result[namespacedKey] = value;
    }
  }
  return result;
}

function placeholders(value: string): string {
  return Array.from(value.matchAll(/\{([A-Za-z]\w*)\}/g), (match) => match[1])
    .sort(compareText)
    .join(",");
}

function compareText(left: string, right: string): number {
  return left.localeCompare(right, "en");
}
