import { applicationEmojis } from "./emojis";
import type { DiscordRestClient } from "./rest";

const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const isRefresh = (value: Record<string, unknown>) => value.type === 2 && typeof value.custom_id === "string" &&
  (typeof value.label === "string" && /^refresh(?: status)?$/iu.test(value.label.trim()) ||
    object(value.emoji) && ["refresh", "🔄", "↻"].includes(String(value.emoji.name)));

/** Apply one refresh treatment at both initial and subsequent message boundaries.
 * Existing panels and less common renderers must not reintroduce text labels. */
export async function normalizeMessageControls(data: Record<string, unknown>, rest: DiscordRestClient): Promise<Record<string, unknown>> {
  const targets: Record<string, unknown>[] = [];
  const clone = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(clone);
    if (!object(value)) return value;
    const result = { ...value };
    if (isRefresh(result)) targets.push(result);
    if (Array.isArray(result.components)) result.components = clone(result.components);
    if (object(result.accessory)) result.accessory = clone(result.accessory);
    return result;
  };
  if (!Array.isArray(data.components)) return data;
  const components = clone(data.components);
  if (!targets.length) return data;
  const inventory = await applicationEmojis(rest).catch(() => undefined);
  const source = inventory?.component("refresh");
  const emoji = source ? { id: source.id, name: source.name, animated: source.animated } : { name: "🔄" };
  for (const target of targets) { delete target.label; target.emoji = { ...emoji }; }
  return { ...data, components };
}
