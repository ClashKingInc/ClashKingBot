import type { DiscordApplicationEmoji } from "./types";
import type { DiscordRestClient } from "./rest";

/** Preserve utility underscores, but normalize punctuation in game names. */
export function emojiName(name: string | number): string {
  return typeof name === "number" ? `th${name}` : name.toLowerCase().replace(/[^a-z0-9_]/gu, "");
}

export class ApplicationEmojis {
  readonly #items: Map<string, DiscordApplicationEmoji>;
  constructor(items: readonly DiscordApplicationEmoji[]) {
    this.#items = new Map(items.filter(item => item.available !== false).map(item => [emojiName(item.name), item]));
  }
  get(name: string | number): string {
    const item = this.component(name);
    return item ? `<${item.animated ? "a" : ""}:${item.name}:${item.id}>` : "";
  }
  component(name: string | number): DiscordApplicationEmoji | undefined {
    const key=emojiName(name);
    // Match the green verified-account artwork in the App and Dashboard.
    // A missing sync must not silently restore the old red verification icon.
    if(key==="account_verified")return this.#items.get("account_verified_green");
    // Corrected resource art removes transparent padding without replacing the
    // original application emoji. Other applications can retain their originals.
    const resources=new Set(["gold","elixir","dark_elixir","capital_gold","clan_games","buildergold","builderelixir","shinyore","glowyore","starryore","no_star"]);
    return (resources.has(key)?this.#items.get(`full_${key}`):undefined)??this.#items.get(key)
      // The API uses e.g. "Legend III"; the asset inventory uses "legendleagueiii".
      ??this.#items.get(key.replace(/(i{1,3})$/u,"league$1"));
  }
  number(number: number, color: "blue" | "gold" = "blue"): string {
    return this.get(`${color}_${number}`) || String(number);
  }
}

type EmojiCacheEntry = { expires: number; value?: ApplicationEmojis; pending?: Promise<ApplicationEmojis> };

// A REST client is created for every interaction. Key by application instead,
// so one isolate shares inventory without mixing Beta and production IDs.
const cache = new Map<string, EmojiCacheEntry>();
export function applicationEmojis(rest: DiscordRestClient): Promise<ApplicationEmojis> {
  const key = rest.applicationId;
  const existing = cache.get(key);
  if (existing?.pending) return existing.pending;
  if (existing?.value && existing.expires > Date.now()) return Promise.resolve(existing.value);
  const entry = existing ?? { expires: 0 };
  const pending = rest.listApplicationEmojis().then(items => {
    entry.value = new ApplicationEmojis(items);
    entry.expires = Date.now() + 300_000;
    return entry.value;
  }).catch((error: unknown) => {
    // Refresh failures must not discard a good inventory or poison the cache
    // with a rejected promise. Briefly back off before retrying stale data.
    if (entry.value) {
      entry.expires = Date.now() + 30_000;
      return entry.value;
    }
    cache.delete(key);
    throw error;
  }).finally(() => { entry.pending = undefined; });
  entry.pending = pending;
  cache.set(key, entry);
  return pending;
}
