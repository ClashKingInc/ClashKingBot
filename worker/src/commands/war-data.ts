import { ClashKingApiError } from "../api/client";
import type { CommandContext } from "./types";

export interface WarAttack {
  attackerTag: string;
  defenderTag: string;
  stars: number;
  destructionPercentage: number;
  order: number;
}
export interface WarMember {
  tag: string;
  name: string;
  townhallLevel: number;
  mapPosition: number;
  attacks?: WarAttack[];
}
export interface WarSide {
  tag: string;
  name: string;
  stars: number;
  destructionPercentage: number;
  members: WarMember[];
  badgeUrls?: { large?: string; small?: string };
}
export interface War {
  state: string;
  teamSize: number;
  attacksPerMember?: number;
  preparationStartTime: string;
  startTime?: string;
  endTime: string;
  clan: WarSide;
  opponent: WarSide;
  tag?: string;
}
interface Pointer {
  clan: { tag: string; publicWarLog: boolean | null };
  opponent: { tag: string; publicWarLog: boolean | null };
  preparationStartTime: string;
  endTime: string;
  type: string;
}
export interface CwlGroup {
  state: string;
  season: string;
  clans: Array<{ tag: string; name: string }>;
  rounds: Array<{ warTags: Array<string | War | { tag: string }> }>;
  warLeague?: { name: string } | null;
}
export const warTime = (value: string) =>
  Date.parse(
    value.replace(
      /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})/u,
      "$1-$2-$3T$4:$5:$6",
    ),
  );
export const compactWarTime = (value: string) =>
  new Date(warTime(value)).toISOString().replace(/[-:]/gu, "");
export function isWar(value: unknown, tag?: string): value is War {
  const war = value as War | undefined;
  return (
    !!war &&
    ["preparation", "inWar", "warEnded"].includes(war.state) &&
    Number.isFinite(war.teamSize) &&
    !!war.clan?.tag &&
    !!war.opponent?.tag &&
    Array.isArray(war.clan.members) &&
    Array.isArray(war.opponent.members) &&
    (!tag || [war.clan.tag, war.opponent.tag].includes(tag))
  );
}
async function optional<T>(
  ctx: CommandContext,
  path: string,
  query: Record<string, string> = {},
) {
  try {
    return await ctx.services.api.get<T>(path, query);
  } catch (error) {
    if (error instanceof ClashKingApiError && [403, 404].includes(error.status))
      return null;
    throw error;
  }
}
export async function loadCwl(
  ctx: CommandContext,
  tag: string,
  season?: string,
): Promise<{ group: CwlGroup; wars: War[] } | null> {
  const encoded = encodeURIComponent(tag),
    current = new Date().toISOString().slice(0, 7);
  if (season && season !== current) {
    const group = await optional<CwlGroup>(ctx, `/v2/cwl/${encoded}/group`, {
      season,
    });
    if (!group || group.season !== season) return null;
    return {
      group,
      wars: group.rounds.flatMap((round) =>
        round.warTags.filter((war): war is War => isWar(war)),
      ),
    };
  }
  const live = await optional<CwlGroup>(
    ctx,
    `/v2/bot/clash/clans/${encoded}/currentwar/leaguegroup`,
  );
  // Never treat a previous month's group as this month's CWL. A requested
  // historical season is served only by the stored-group endpoint above.
  if (live && live.season === current && live.state !== "notInWar") {
    const tags = [
      ...new Set(
        live.rounds
          .flatMap((round) => round.warTags)
          .filter(
            (v): v is string =>
              typeof v === "string" &&
              /^#[0289PYLQGRJCUV]+$/u.test(v) &&
              v !== "#0",
          ),
      ),
    ];
    if (tags.length > 64) throw new Error("Unexpected CWL group size");
    const wars: War[] = [];
    for (let i = 0; i < tags.length; i += 4) {
      for (const war of await Promise.all(
        tags
          .slice(i, i + 4)
          .map((warTag) =>
            optional<War>(
              ctx,
              `/v2/bot/clash/clanwarleagues/wars/${encodeURIComponent(warTag)}`,
            ).then((war) => (war ? { ...war, tag: warTag } : null)),
          ),
      ))
        if (isWar(war)) wars.push(war);
    }
    return { group: live, wars };
  }
  const stored = await optional<CwlGroup>(ctx, `/v2/cwl/${encoded}/group`, {
    season: current,
  });
  return stored && stored.season === current
    ? {
        group: stored,
        wars: stored.rounds.flatMap((round) =>
          round.warTags.filter((war): war is War => isWar(war)),
        ),
      }
    : null;
}
export function latestWar(wars: War[], tag: string) {
  const priority = (war: War) =>
    war.state === "inWar" ? 3 : war.state === "preparation" ? 2 : 1;
  return wars
    .filter((war) => isWar(war, tag))
    .sort(
      (a, b) =>
        priority(b) - priority(a) || warTime(b.endTime) - warTime(a.endTime),
    )[0];
}
export async function loadCurrentWar(
  ctx: CommandContext,
  tag: string,
): Promise<{ war?: War; privateLog: boolean; cwl: boolean }> {
  let current: War | null = null,
    privateLog = false;
  try {
    current = await ctx.services.api.get<War>(
      `/v2/bot/clash/clans/${encodeURIComponent(tag)}/currentwar`,
    );
  } catch (error) {
    if (
      !(error instanceof ClashKingApiError) ||
      ![403, 404].includes(error.status)
    )
      throw error;
    privateLog = error.status === 403;
  }
  if (isWar(current, tag)) return { war: current, privateLog, cwl: false };
  const pointer = await optional<Pointer>(
    ctx,
    `/v2/war/${encodeURIComponent(tag)}/basic`,
  );
  if (
    pointer &&
    !["cwl", "league"].some((type) =>
      pointer.type.toLowerCase().includes(type),
    ) &&
    [pointer.clan.tag, pointer.opponent.tag].includes(tag)
  ) {
    const other = pointer.clan.tag === tag ? pointer.opponent : pointer.clan;
    if (other.publicWarLog !== false) {
      const candidate = await optional<War>(
        ctx,
        `/v2/bot/clash/clans/${encodeURIComponent(other.tag)}/currentwar`,
      );
      // Opponent discovery is valid only for the saved pairing AND schedule.
      // A public opponent's next matchup must never stand in for our private war.
      if (
        isWar(candidate, tag) &&
        [candidate.clan.tag, candidate.opponent.tag].includes(other.tag) &&
        Number.isFinite(warTime(pointer.endTime)) &&
        Number.isFinite(warTime(pointer.preparationStartTime)) &&
        warTime(candidate.endTime) === warTime(pointer.endTime) &&
        warTime(candidate.preparationStartTime) ===
          warTime(pointer.preparationStartTime)
      )
        return { war: candidate, privateLog, cwl: false };
    }
  }
  const cwl = await loadCwl(ctx, tag),
    war = cwl && latestWar(cwl.wars, tag);
  return { war: war || undefined, privateLog, cwl: !!war };
}

// Preserve the group's round positions even when an earlier war is unavailable.
// Filtering to fetched wars before indexing would silently shift round numbers.
export function clanRounds(
  group: CwlGroup,
  wars: War[],
  tag: string,
): Array<War | undefined> {
  return group.rounds.map((round) =>
    round.warTags
      .map((value) =>
        typeof value === "string"
          ? wars.find((war) => war.tag === value)
          : isWar(value)
            ? value
            : wars.find((war) => war.tag === value.tag),
      )
      .find((war) => isWar(war, tag)),
  );
}
