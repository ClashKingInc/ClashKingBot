import { DiscordRestError } from "../discord/rest";
import type { DiscordMember, DiscordRole } from "../discord/types";
import type { CommandServices } from "../commands/types";
import { planRefresh, type RefreshCategory, type RefreshData } from "./plan";

export interface RefreshJob {
  id: string; server_id: string; user_id: string; request_id: string | null;
  token: string; expires_at: string; preview: boolean; categories: RefreshCategory[]; roster_role_ids?: string[]; role_treatment?: "add" | "remove" | "both";
  auto_role_treatment?: "add" | "remove" | "both"; auto_role_blacklist_ids?: string[];
}
interface GuildState { roles: DiscordRole[]; bot: DiscordMember; owner: string }
const permissions = (state: GuildState) => state.roles.filter(role => role.id === state.bot.user?.id || state.bot.roles.includes(role.id)
  || role.name === "@everyone").reduce((bits, role) => bits | BigInt(String(role.permissions ?? "0")), 0n);
const higher = (left: DiscordRole, right: DiscordRole) => Number(left.position) > Number(right.position)
  || Number(left.position) === Number(right.position) && BigInt(left.id) < BigInt(right.id);
const topRole = (roles: DiscordRole[], member: DiscordMember) => roles.filter(role => member.roles.includes(role.id))
  .reduce<DiscordRole | undefined>((top, role) => !top || higher(role, top) ? role : top, undefined);

export async function processRefreshJob(services: CommandServices, job: RefreshJob, state: GuildState) {
  const rest = services.discordRest;
  // These settings only govern legacy game-driven automatic evaluation.
  // Roster membership and tenure jobs have independent explicit contracts.
  const gameAutomatic = !job.request_id && !job.categories.every(category => ["tenure","roster"].includes(category));
  const treatment = (gameAutomatic ? job.auto_role_treatment : job.role_treatment) ?? "both";
  if (!["add", "remove", "both"].includes(treatment)) throw new Error("Invalid role treatment");
  let member: DiscordMember;
  try { member = await rest.getGuildMember(job.server_id, job.user_id); }
  catch (error) {
    if (error instanceof DiscordRestError && error.status === 404) return { skipped: "Member left the server", add: [], remove: [], blocked: [] };
    throw error;
  }
  if (member.user?.bot) return { skipped: "Bot member", add: [], remove: [], blocked: [] };
  if (gameAutomatic && job.auto_role_blacklist_ids?.some(role => member.roles.includes(role))) {
    return { skipped: "Automatic refresh excluded by a server role", add: [], remove: [], blocked: [] };
  }
  const data = await services.api.get<RefreshData>(`/v2/bot/role-refresh/${job.server_id}/data`, { userId: job.user_id });
  if (!job.request_id && !data.settings.autoeval_enabled && !job.categories.every(category=>["tenure","roster"].includes(category))) return { skipped: "Automatic refresh disabled", add: [], remove: [], blocked: [] };
  data.retiredRosterRoleIds=job.roster_role_ids??[];
  const plan = planRefresh(data, member.roles, job.categories, {
    username: member.user?.global_name ?? member.user?.username ?? "",
    joinedAt: member.joined_at,
    displayName: member.nick ?? member.user?.global_name ?? member.user?.username ?? "",
  }, !job.request_id);
  const botTop = topRole(state.roles, state.bot), memberTop = topRole(state.roles, member);
  const bits = permissions(state), admin = (bits & 8n) !== 0n;
  const blocked: string[] = [];
  const editable = (id: string) => {
    const role = state.roles.find(role => role.id === id);
    if (!role) { blocked.push(`${id}: role no longer exists`); return false; }
    if (id === job.server_id || role.managed || !botTop || !higher(botTop, role) || (!admin && (bits & (1n << 28n)) === 0n)) {
      blocked.push(`${id}: missing permission or role is above the bot`); return false;
    }
    return true;
  };
  // Role treatment never disables nickname updates. Filter before checking
  // editable roles so a deliberately skipped direction is not reported blocked.
  const add = (treatment === "remove" ? [] : plan.add).filter(editable);
  const remove = (treatment === "add" ? [] : plan.remove).filter(editable);
  let nickname = plan.nickname;
  if (nickname !== undefined && (state.owner === job.user_id || !botTop || memberTop && !higher(botTop, memberTop)
    || !admin && (bits & (1n << 27n)) === 0n)) {
    blocked.push("nickname: missing permission or member is above the bot"); nickname = undefined;
  }
  if (!job.preview) {
    const valid = await services.api.post<{ valid: boolean }>("/v2/bot/role-refresh/validate", {
      id: job.id, token: job.token, accountTags: data.accounts.map(account => account.tag), rosterFingerprint: data.roster?.fingerprint,
      ...(gameAutomatic ? {automaticRoleTreatment: treatment, automaticBlacklistRoles: job.auto_role_blacklist_ids ?? []} : {}),
    });
    if (!valid.valid) throw new Error("Refresh inputs changed; retry with current accounts");
    // Individual role endpoints preserve unrelated/concurrent role assignments.
    // Apply additions first so moving family clans does not briefly drop access.
    const checkDeadline = () => { if (Date.now() >= Date.parse(job.expires_at) - 15_000) throw new Error("Refresh lease deadline exceeded"); };
    for (const role of add) { checkDeadline(); await rest.request(`/guilds/${job.server_id}/members/${job.user_id}/roles/${role}`, { method: "PUT" }); }
    for (const role of remove) { checkDeadline(); await rest.request(`/guilds/${job.server_id}/members/${job.user_id}/roles/${role}`, { method: "DELETE" }); }
    if (nickname !== undefined) { checkDeadline(); await rest.request(`/guilds/${job.server_id}/members/${job.user_id}`, { method: "PATCH", body: JSON.stringify({ nick: nickname }) }); }
  }
  return { add, remove, ...(nickname === undefined ? {} : { nickname }), blocked, preview: job.preview, mainTag: plan.mainTag };
}

export async function drainRefreshJobs(services: CommandServices, requestId?: string, serverId?: string) {
  const { jobs } = await services.api.post<{ jobs: RefreshJob[] }>("/v2/bot/role-refresh/claim", {
    includeRoster: true, includeRoleTreatment: true, includeAutomaticPolicy: true, ...(requestId ? { requestId } : { includeTenure: true }), ...(serverId ? { serverId } : {}),
  });
  const states = new Map<string, Promise<GuildState>>();
  let botId: Promise<string> | undefined;
  // Bounded fan-out for bulk refreshes. Roles and the bot member are loaded once
  // per guild per batch, while each target member is read immediately before use.
  for (let start = 0; start < jobs.length; start += 2) {
    await Promise.all(jobs.slice(start, start + 2).map(async job => {
      try {
        let state = states.get(job.server_id);
        if (!state) {
          botId ??= services.discordRest.get<{ id: string }>("/users/@me").then(user => user.id);
          state = Promise.all([services.discordRest.getGuildRoles(job.server_id),
            botId.then(id => services.discordRest.getGuildMember(job.server_id, id)), services.discordRest.getGuild(job.server_id)])
            .then(([roles, bot, guild]) => ({ roles, bot, owner: String(guild.owner_id) }));
          states.set(job.server_id, state);
        }
        const result = await processRefreshJob(services, job, await state);
        await services.api.post("/v2/bot/role-refresh/complete", { id: job.id, token: job.token, success: true, result });
      } catch {
        // Partial external delivery is retried by computing a fresh delta; role
        // PUT/DELETE are idempotent. Never log provider bodies or linked accounts.
        await services.api.post("/v2/bot/role-refresh/complete", { id: job.id, token: job.token, success: false,
          result: { error: "Refresh could not finish; retry queued" } });
      }
    }));
  }
  return jobs.length;
}
