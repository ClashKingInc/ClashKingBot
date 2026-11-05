import { actionRow, type ActionRowComponent } from "../discord/components";

export interface ClanChoice { tag: string; name: string }

/** Keep offsets fixed: previous/next controls must not change which clans a page owns. */
export function clanSelector(input: {
  clans: readonly ClanChoice[];
  selectedTag?: string;
  page: number;
  customId: string;
  includeAll?: { label: string; value: "all" };
}): { row: ActionRowComponent; page: number } {
  const clans = [...input.clans].sort((a, b) => a.name.localeCompare(b.name) || a.tag.localeCompare(b.tag));
  const size = input.includeAll ? 22 : 23;
  const last = Math.max(0, Math.ceil(clans.length / size) - 1);
  const page = Math.max(0, Math.min(Number.isSafeInteger(input.page) ? input.page : 0, last));
  const options = [
    ...(input.includeAll ? [{ ...input.includeAll, default: input.selectedTag === "all" }] : []),
    ...(page > 0 ? [{ label: "← Previous clans", value: `page:${page - 1}` }] : []),
    ...clans.slice(page * size, (page + 1) * size).map(clan => ({
      label: clan.name.slice(0, 100), description: clan.tag,
      value: clan.tag, default: clan.tag === input.selectedTag,
    })),
    ...(page < last ? [{ label: "More clans →", value: `page:${page + 1}` }] : []),
  ];
  const selected = clans.find(clan => clan.tag === input.selectedTag);
  return { page, row: actionRow({ type: 3, custom_id: input.customId,
    placeholder: (selected?.name ?? "Choose a clan").slice(0, 150), min_values: 1, max_values: 1,
    options: options.length ? options : [{ label: "No clans", value: "none" }], disabled: clans.length === 0,
  }) };
}
