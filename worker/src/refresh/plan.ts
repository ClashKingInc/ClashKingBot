export const refreshCategories = ["family", "clan", "leadership", "townhall", "builderhall", "league", "builder_league", "category", "nicknames"] as const;
export type RefreshCategory = typeof refreshCategories[number];
export interface RefreshRule { type: string; option: string; role_id: string; clan_tag?: string | null }
export interface RefreshPlayer {
  tag: string; name: string; townHallLevel: number; builderHallLevel?: number; trophies?: number;
  bestTrophies?: number; bestBuilderBaseTrophies?: number; warStars?: number; role?: string;
  clan?: { tag: string; name: string }; league?: { name: string }; leagueTier?: { name: string }; builderBaseLeague?: { name: string };
}
export interface RefreshData {
  rules: RefreshRule[];
  clans: Array<{ tag: string; category?: string | null; abbreviation: string }>;
  accounts: RefreshPlayer[];
  mainTag?: string | null;
  settings: { change_nickname: boolean; auto_eval_nickname: boolean; flair_non_family: boolean;
    nickname_rule: string; non_family_nickname_rule: string; autoeval_enabled: boolean };
}
export function ruleCategory(rule: RefreshRule): RefreshCategory | undefined {
  if (rule.type === "clan_role") return rule.option === "member" ? "clan" : "leadership";
  if (rule.type === "clan_category") return "category";
  return refreshCategories.includes(rule.type as RefreshCategory) ? rule.type as RefreshCategory : undefined;
}
const leagueKey = (name: string) => name.toLowerCase().replaceAll(/[^a-z0-9]+/gu, "_").replace(/_$/u, "");
const level = (value: string) => Number(value.replace(/^(?:th|bh)/iu, ""));
const position = (value?: string) => ({ admin: "elder", coLeader: "co_leader", leader: "leader", member: "member" })[value ?? ""] ?? value;

/** All accounts here have already been filtered by the authoritative link query.
 * Evaluate every configured predicate before narrowing the managed role set:
 * a shared role still belongs to someone who earns it in an unselected category. */
export function planRefresh(data: RefreshData, currentRoles: readonly string[], categories: readonly RefreshCategory[],
  discord: { username: string; displayName: string }, automatic = false) {
  const familyTags = new Set(data.clans.map(clan => clan.tag));
  const family = data.accounts.some(player => player.clan && familyTags.has(player.clan.tag));
  const desired = new Set<string>();
  const managed = new Set<string>();
  for (const rule of data.rules) {
    const category = ruleCategory(rule);
    // This refresh does not implement tenure/status/achievement rules. Leave
    // their roles untouched; do not imply another consumer delivers them.
    if (!category) continue;
    if (categories.includes(category)) managed.add(rule.role_id);
    let earned = false;
    if (rule.type === "family") earned = data.accounts.length > 0 && (rule.option === "family" ? family : !family);
    else earned = data.accounts.some(player => {
      const clan = data.clans.find(item => item.tag === player.clan?.tag);
      if (rule.type === "clan_role") return !!clan && (!rule.clan_tag || rule.clan_tag === clan.tag)
        && (rule.option === "member" || (rule.clan_tag && rule.option === "leader" ? ["co_leader", "leader"].includes(position(player.role) ?? "") : position(player.role) === rule.option));
      if (rule.type === "clan_category") return !!clan && clan.category === rule.option;
      if (!clan && !data.settings.flair_non_family) return false;
      if (rule.type === "townhall") return level(rule.option) === player.townHallLevel;
      if (rule.type === "builderhall") return level(rule.option) === player.builderHallLevel;
      if (rule.type === "league" || rule.type === "builder_league") {
        const builder = rule.type === "builder_league";
        const best = builder ? player.bestBuilderBaseTrophies ?? 0 : player.bestTrophies ?? 0;
        if (/^\d+_personal_best$/u.test(rule.option)) {
          const thresholds = builder ? [7000, 6000, 5000] : [6000, 5000];
          return thresholds.find(threshold => best >= threshold) === Number(rule.option.split("_")[0]);
        }
        const name = (builder ? player.builderBaseLeague : player.leagueTier ?? player.league)?.name;
        if (!name || name === "Unranked") return false;
        const key = leagueKey(name);
        return key === rule.option || (key === "legend_league" && rule.option === "legends_league")
          || (key.replace(/_(?:i|ii|iii|iv|v)$/u, "") === rule.option);
      }
      return false;
    });
    if (earned) desired.add(rule.role_id);
  }
  const current = new Set(currentRoles);
  const add = [...managed].filter(role => desired.has(role) && !current.has(role));
  const remove = [...managed].filter(role => !desired.has(role) && current.has(role));
  const main = data.accounts.find(player => player.tag === data.mainTag)
    ?? [...data.accounts].sort((a, b) => Number(familyTags.has(b.clan?.tag ?? "")) - Number(familyTags.has(a.clan?.tag ?? ""))
      || b.townHallLevel - a.townHallLevel || (b.trophies ?? 0) - (a.trophies ?? 0) || a.tag.localeCompare(b.tag))[0];
  let nickname: string | undefined;
  if (main && categories.includes("nicknames") && data.settings.change_nickname && (!automatic || data.settings.auto_eval_nickname)) {
    const superscript = "⁰¹²³⁴⁵⁶⁷⁸⁹";
    const values: Record<string, string> = {
      discord_name: discord.username, discord_display_name: discord.displayName,
      player_name: main.name, player_tag: main.tag, player_townhall: String(main.townHallLevel),
      player_townhall_small: String(main.townHallLevel).replace(/\d/gu, digit => superscript[Number(digit)]!),
      player_warstars: String(main.warStars ?? 0), player_role: ({ elder: "Elder", co_leader: "Co-Leader", leader: "Leader", member: "Member" })[position(main.role) ?? ""] ?? "",
      player_clan: main.clan?.name ?? "", player_league: main.leagueTier?.name ?? main.league?.name ?? "Unranked",
      player_clan_abbreviation: data.clans.find(clan => clan.tag === main.clan?.tag)?.abbreviation ?? "",
    };
    values.clan_abbr = values.player_clan_abbreviation!;
    nickname = (family ? data.settings.nickname_rule : data.settings.non_family_nickname_rule)
      .replace(/\{([a-z_]+)\}/gu, (token, key: string) => values[key] ?? token).trim();
    nickname = [...nickname].slice(0, 32).join("");
    if (!nickname || nickname === discord.displayName) nickname = undefined;
  }
  return { add, remove, nickname, mainTag: main?.tag };
}
