import { ClashKingApiError } from "../api/client";
import { DiscordRestError } from "../discord/rest";
import type { DiscordMember, DiscordRole } from "../discord/types";
import type { CommandServices } from "../commands/types";
import { planRefresh, type RefreshCategory, type RefreshData } from "./plan";

export interface RefreshJob {
  id: string; server_id: string; user_id: string; request_id: string | null;
  token: string; expires_at: string; preview: boolean; categories: RefreshCategory[]; roster_role_ids?: string[]; role_treatment?: "add" | "remove" | "both";
  auto_role_treatment?: "add" | "remove" | "both"; auto_role_blacklist_ids?: string[];
}
export interface GuildState { roles: DiscordRole[]; bot: DiscordMember; owner: string }
const permissions = (state: GuildState) => state.roles.filter(role => role.id === state.bot.user?.id || state.bot.roles.includes(role.id)
  || role.name === "@everyone").reduce((bits, role) => bits | BigInt(String(role.permissions ?? "0")), 0n);
const higher = (left: DiscordRole, right: DiscordRole) => Number(left.position) > Number(right.position)
  || Number(left.position) === Number(right.position) && BigInt(left.id) < BigInt(right.id);
const topRole = (roles: DiscordRole[], member: DiscordMember) => roles.filter(role => member.roles.includes(role.id))
  .reduce<DiscordRole | undefined>((top, role) => !top || higher(role, top) ? role : top, undefined);

type ManualRefresh = { server_id:string; user_id:string; preview:boolean; categories:RefreshCategory[]; role_treatment:"add"|"remove"|"both"; manual:true };
export async function processManualRefresh(services:CommandServices, input:ManualRefresh,state:GuildState) {
  return processMemberRefresh(services,input,state);
}
export async function processRefreshJob(services:CommandServices,job:RefreshJob,state:GuildState) {
  return processMemberRefresh(services,job,state);
}
async function processMemberRefresh(services: CommandServices, job: RefreshJob|ManualRefresh, state: GuildState) {
  const manual="manual" in job;
  const rest = services.discordRest;
  // These settings only govern legacy game-driven automatic evaluation.
  // Roster membership and tenure jobs have independent explicit contracts.
  const gameAutomatic = !manual && !job.request_id && !job.categories.every(category => ["tenure","roster"].includes(category));
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
  if (!manual && !job.request_id && !data.settings.autoeval_enabled && !job.categories.every(category=>["tenure","roster"].includes(category))) return { skipped: "Automatic refresh disabled", add: [], remove: [], blocked: [] };
  data.retiredRosterRoleIds=manual?[]:job.roster_role_ids??[];
  // Tenure work is paused; existing tenure grants remain unmanaged.
  const plan = planRefresh(data, member.roles, job.categories.filter(category => category !== "tenure"), {
    username: member.user?.global_name ?? member.user?.username ?? "",
    joinedAt: member.joined_at,
    displayName: member.nick ?? member.user?.global_name ?? member.user?.username ?? "",
  }, !manual && !job.request_id);
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
    if (!manual) {
    const valid = await services.api.post<{ valid: boolean }>("/v2/bot/role-refresh/validate", {
      id: job.id, token: job.token, accountTags: data.accounts.map(account => account.tag), rosterFingerprint: data.roster?.fingerprint,
      ...(gameAutomatic ? {automaticRoleTreatment: treatment, automaticBlacklistRoles: job.auto_role_blacklist_ids ?? []} : {}),
    });
    if (!valid.valid) throw new Error("Refresh inputs changed; retry with current accounts");
    }
    const checkDeadline = () => { if (!manual && Date.now() >= Date.parse(job.expires_at) - 15_000) throw new Error("Refresh lease deadline exceeded"); };
    if(add.length||remove.length||nickname!==undefined){
      checkDeadline();
      // Discord accepts roles and nickname in one member PATCH. Merge the
      // managed delta into a fresh membership read so unrelated assignments
      // added while player data was loading are retained. The member lease
      // serializes our workers; Discord offers no conditional external edit.
      const current=await rest.getGuildMember(job.server_id,job.user_id);
      const merged=[...new Set([...current.roles.filter(id=>!remove.includes(id)),...add])];
      checkDeadline();
      await rest.request(`/guilds/${job.server_id}/members/${job.user_id}`,{method:"PATCH",body:JSON.stringify({...(add.length||remove.length?{roles:merged}:{}),...(nickname!==undefined?{nick:nickname}:{})})});
    }
  }
  return { displayName:nickname??member.nick??member.user?.global_name??member.user?.username, add, remove, ...(nickname === undefined ? {} : { nickname }), blocked, preview: job.preview, mainTag: plan.mainTag };
}

export async function drainRefreshJobs(services: CommandServices, requestId?: string, serverId?: string) {
  const { jobs } = await services.api.post<{ jobs: RefreshJob[] }>("/v2/bot/role-refresh/claim", {
    includeRoster: true, includeRoleTreatment: true, includeAutomaticPolicy: true, ...(requestId ? { requestId } : { automaticOnly: true }), ...(serverId ? { serverId } : {}),
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
      } catch (error) {
        let retryAfterSeconds:number|undefined;
        if(error instanceof DiscordRestError&&error.status===429)retryAfterSeconds=error.retryAfterSeconds??1;
        if(error instanceof ClashKingApiError&&error.status===429){try{const body=JSON.parse(error.body);retryAfterSeconds=error.retryAfterSeconds??Number(body.retryAfterSeconds??body.retry_after??30);}catch{retryAfterSeconds=30;}}

        // Partial external delivery is retried by computing a fresh delta; role
        // PUT/DELETE are idempotent. Never log provider bodies or linked accounts.
        await services.api.post("/v2/bot/role-refresh/complete", { id: job.id, token: job.token, success: false,
          ...(retryAfterSeconds?{retryAfterSeconds}:{}), result: { error: retryAfterSeconds?"Waiting for Discord; refresh will continue automatically.":"Refresh could not finish; retry queued" } });
      }
    }));
  }
  return jobs.length;
}
