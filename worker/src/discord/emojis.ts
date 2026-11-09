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
  warStars(stars: number): string {
    const earned = Number.isFinite(stars) ? Math.max(0, Math.min(3, Math.trunc(stars))) : 0;
    return this.get("war_star").repeat(earned) + this.get("no_star").repeat(3 - earned);
  }
  component(name: string | number): DiscordApplicationEmoji | undefined {
    const key=emojiName(name);
    // Match the green verified-account artwork in the App and Dashboard.
    // A missing sync must not silently restore the old red verification icon.
    if(key==="account_verified")return this.#items.get("account_verified")??this.#items.get("account_verified_green");
    // These two assets share the same visible bounds; the empty star has an
    // outline instead of a miniature filled star. Keep originals for rollback.
    if(key==="war_star")return this.#items.get("war_star_filled")??this.#items.get(key);
    if(key==="no_star")return this.#items.get("war_star_empty")??this.#items.get("full_no_star")??this.#items.get(key);
    // Gold, elixir and dark elixir use their canonical, fitted application emoji.
    // Retain existing aliases for the other resource types.
    const resources=new Set(["capital_gold","clan_games","buildergold","builderelixir","shinyore","glowyore","starryore"]);
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
