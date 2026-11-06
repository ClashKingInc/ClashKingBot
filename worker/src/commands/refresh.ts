import { emojis, escapeMarkdown } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import { sendInteractionError } from "./errors";
import { localizations } from "../localization/catalog";
import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, InteractionType } from "../discord/types";
import type { Env } from "../env";
import { refreshCategories, type RefreshCategory } from "../refresh/plan";
import { CommandInputError, invokingUserId, OptionType, requireGuildId, stringOption } from "./command-utils";
import type { Command, CommandContext, CommandServices } from "./types";

const labels: Record<RefreshCategory, string> = { roster: "Roster membership", tenure: "Discord tenure", family: "Family membership", clan: "Clan membership", leadership: "Clan leadership",
  townhall: "Town Hall", builderhall: "Builder Hall", league: "Home Village league", builder_league: "Builder Base league", category: "Clan category", nicknames: "Nickname" };
type RoleTreatment = "add" | "remove" | "both";
const roleTreatment = (value: string | undefined): RoleTreatment => {
  if (value === undefined) return "both";
  if (value !== "add" && value !== "remove" && value !== "both") throw new CommandInputError("Choose Add only, Remove only, or Both");
  return value;
};
const bool = (ctx: CommandContext, name: string) => ctx.options.get(name)?.value === true;
export const refreshCommand: Command = {
  deferred: true,
  definition: { description_localizations: localizations("refresh.description"), name: "refresh", description: "Refresh your roles and nickname, or refresh a member or role", type: 1, contexts: [0], integration_types: [0],
    options: [
      { name: "role_or_user", description: "Member or role to refresh (defaults to yourself)", type: OptionType.Mentionable },
      { name: "test", description: "Preview the changes without applying them", type: OptionType.Boolean },
      { name: "role_treatment", description: "Only add roles, only remove roles, or both (nickname is independent)", type: OptionType.String,
        choices: [{ name: "Both", value: "both" }, { name: "Add only", value: "add" }, { name: "Remove only", value: "remove" }] },
      { name: "advanced_mode", description: "Choose which role categories and nickname to refresh", type: OptionType.Boolean },
    ] },
  async execute(ctx) {
    requireGuildId(ctx);
    const treatment = roleTreatment(stringOption(ctx, "role_treatment"));
    const target = stringOption(ctx, "role_or_user") ?? invokingUserId(ctx);
    const kind = ctx.interaction.data?.resolved?.roles?.[target] ? "role" : "user";
    if (bool(ctx, "advanced_mode")) return legacyMessage({ embeds:[{color:await serverEmbedColor(ctx),title:"Role Refresh",description:"Choose which role types to refresh."}], components: [actionRow({
      type: 3, custom_id: `ck:refresh:choose:${invokingUserId(ctx)}:${kind}:${target}:${bool(ctx, "test") ? "1" : "0"}:${treatment}`,
      min_values: 1, max_values: refreshCategories.length,
      options: refreshCategories.map(value => ({ label: labels[value], value })),
    })] });
    return runManualRefresh(ctx, kind, target, bool(ctx, "test"), [...refreshCategories], treatment);
  },
};

interface ManualResult {user_id:string;result:{displayName?:string;add?:string[];remove?:string[];nickname?:string;blocked?:string[];preview?:boolean;skipped?:string;error?:string}}
interface ManualReport {requestId:string;actorId:string;channelId:string;messageId:string|null;createdAt:string;updatedAt:string;finished:boolean;results:ManualResult[];total:number;completed:number;failed:number;target:string;kind:string;preview:boolean;categories:RefreshCategory[];treatment:RoleTreatment}
async function runManualRefresh(ctx: CommandContext, kind: string, target: string, preview: boolean, categories: RefreshCategory[], treatment: RoleTreatment = "both") {
  const guild=requireGuildId(ctx),actor=invokingUserId(ctx),channelId=ctx.interaction.channel_id;
  if(!channelId)throw new CommandInputError("Run refresh in a server channel.");
  const requestId=ctx.interaction.id;
  // A public deferred response is a durable channel message. Store its ID
  // before enqueueing work, then edit it with bot auth after the token expires.
  const original=await ctx.services.discordRest.getOriginalInteractionResponse(ctx.interaction.token);
  await ctx.services.api.post(`/v2/bot/role-refresh/${guild}/manual-start`,{actorId:actor,requestId,channelId,messageId:original.id,targetId:target,targetKind:kind,preview,categories,treatment});
  return status(ctx,requestId);

}

async function publishManualRefresh(ctx:CommandContext,guild:string,requestId:string){
  const report=await ctx.services.api.get<ManualReport>(`/v2/bot/role-refresh/${guild}/manual-progress`,{requestId});
  const payload=(await status(ctx,requestId,0,report)).data??{};
  const messageId=report.messageId;
  if(!messageId)return;
  await ctx.services.discordRest.editChannelMessage(report.channelId,messageId,payload);
  await ctx.services.api.post(`/v2/bot/role-refresh/${guild}/manual-progress?requestId=${requestId}`,{messageId,updatedAt:report.updatedAt,finished:report.finished});
  return messageId;
}

export async function publishManualRefreshes(services:CommandServices,env:Env){
  const {requests}=await services.api.get<{requests:{id:string;server_id:string}[]}>("/v2/bot/role-refresh/progress");
  for(const request of requests){
    try{
      const report=await services.api.get<ManualReport>(`/v2/bot/role-refresh/${request.server_id}/manual-progress`,{requestId:request.id});
      // This context is only for the shared renderer. It is never dispatched as
      // an interaction, and contains no stored interaction token.
      const ctx:CommandContext={env,services,locale:"en-US",options:new Map(),path:[],interaction:{id:request.id,application_id:env.DISCORD_APPLICATION_ID,type:InteractionType.ApplicationCommand,token:"",version:1,guild_id:request.server_id,channel_id:report.channelId,user:{id:report.actorId,username:""}}};
      await publishManualRefresh(ctx,request.server_id,request.id);
    }catch{console.error("Manual refresh progress could not be published",{requestId:request.id});}
  }
  return requests;
}

async function status(ctx: CommandContext, requestId: string, requestedPage=0, supplied?:ManualReport) {
  const guild = requireGuildId(ctx),size=10;
  const report=supplied??await ctx.services.api.get<ManualReport>(`/v2/bot/role-refresh/${guild}/manual-report`,{requestId,actorId:invokingUserId(ctx)});
  if(!report.finished){
    const processed=report.completed+report.failed,elapsed=Math.max(0,Math.floor((Date.now()-Date.parse(report.createdAt))/1000));
    return legacyMessage({allowed_mentions:{parse:[]},embeds:[{color:await serverEmbedColor(ctx),title:"Role Refresh In Progress",description:`**${processed} / ${report.total} members processed**\n${report.failed?`${report.failed} could not be refreshed.\n`:""}This message updates as the refresh continues.`,footer:{text:`Time Elapsed: ${elapsed} seconds${report.preview?" | Test mode":""}`}}]});
  }
  const visible=report.results.filter(({result})=>result.error||result.skipped||result.blocked?.length||result.add?.length||result.remove?.length||result.nickname);
  const last=Math.max(0,Math.ceil(visible.length/size)-1),page=Math.min(requestedPage,last);
  const result={...report,results:visible.slice(page*size,(page+1)*size)};
  const [server,emoji,identities]=await Promise.all([
    ctx.services.discordRest.getGuild(guild),emojis(ctx),
    Promise.all(result.results.map(item=>ctx.services.discordRest.getGuildMember(guild,item.user_id).catch(()=>undefined))),
  ]);
  const roleList=(ids:string[]|undefined)=>ids?.length?ids.map(id=>`<@&${id}>`).join(' '):'None';
  const blocks=result.results.map((item,index)=>{
    const value=item.result,member=identities[index],name=value.displayName??member?.nick??member?.user?.global_name??member?.user?.username??`Member ${item.user_id}`;
    const lines=[name?`**${escapeMarkdown(name)}** (<@${item.user_id}>)`:`<@${item.user_id}>`];
    if(value.skipped)lines.push(escapeMarkdown(value.skipped));
    else if(value.error)lines.push(escapeMarkdown(value.error));
    else{
      if(value.add?.length)lines.push(`**${value.preview?'Would add':'Added'}:** ${roleList(value.add)}`);
      if(value.remove?.length)lines.push(`**${value.preview?'Would remove':'Removed'}:** ${roleList(value.remove)}`);
      if(value.nickname)lines.push(`**Name Change:** ${escapeMarkdown(value.nickname)}`);
      if(value.blocked?.length)lines.push(`**Blocked:** ${value.blocked.map(entry=>{const match=/^(\d{15,20}): (.*)$/u.exec(entry);return match?`<@&${match[1]}>: ${escapeMarkdown(match[2]!)}`:escapeMarkdown(entry);}).join('; ')}`);
    }
    return lines.join('\n');
  });
  const chunks=[''];
  for(const block of blocks){if(chunks.at(-1)!.length+block.length+2>3500)chunks.push('');chunks[chunks.length-1]+=(chunks.at(-1)?'\n\n':'')+block;}
  const complete=report.finished,preview=report.preview;
  const unchanged=report.results.filter(({result})=>!result.error&&!result.skipped&&!result.blocked?.length&&!result.add?.length&&!result.remove?.length&&!result.nickname).length;
  const footer=[`${result.completed}/${result.total} members refreshed`,unchanged?`${unchanged} unchanged`:null,result.failed?`${result.failed} failed`:null,preview?'Test mode':null].filter(Boolean).join(' | ');
  const color=await serverEmbedColor(ctx),title=result.failed?'Refresh Incomplete':complete?'Refresh Complete':'Role Refresh In Progress';
  const id=(index:number)=>`ck:refresh:status:${report.actorId}:${requestId}:${index}`;
  return legacyMessage({allowed_mentions:{parse:[]},embeds:chunks.map((description,index)=>({color,...(index===0?{author:{name:server.name,...(server.icon?{icon_url:`https://cdn.discordapp.com/icons/${guild}/${server.icon}.png`}:{})},title}:{}),description:description||'No changes needed.',...(index===chunks.length-1?{footer:{text:footer}}:{})})),components:[actionRow(
    ...(last>0?[
      {type:2 as const,style:2 as const,label:'‹',custom_id:id(page-1),disabled:page===0},
      {type:2 as const,style:2 as const,label:`${page+1} / ${last+1}`,custom_id:`${id(page)}:counter`,disabled:true},
      {type:2 as const,style:2 as const,label:'›',custom_id:id(page+1),disabled:page===last},
    ]:[]),
    {type:2,style:2,emoji:emoji.component('refresh')??{name:'↻'},custom_id:`ck:refresh:again:${report.actorId}:${requestId}`},
  )]});
}

export async function dispatchRefresh(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  if (ctx.interaction.type !== InteractionType.MessageComponent) throw new CommandInputError("Invalid refresh action");
  const [, , action, actor, first, second, preview, treatment] = (ctx.interaction.data?.custom_id ?? "").split(":");
  if (actor !== invokingUserId(ctx)) throw new CommandInputError("This refresh menu belongs to another person");
  const run = async () => {
    if(action==="again"&&first&&/^\d{15,20}$/u.test(first)){
      const report=await ctx.services.api.get<ManualReport>(`/v2/bot/role-refresh/${requireGuildId(ctx)}/manual-report`,{requestId:first,actorId:invokingUserId(ctx)});
      return runManualRefresh(ctx,report.kind,report.target,report.preview,report.categories,report.treatment);
    }
    if (action === "status" && first && /^\d{15,20}$/u.test(first)){
      const page=Number(second??0);if(!Number.isSafeInteger(page)||page<0||page>=300)throw new CommandInputError("Invalid refresh page.");
      return status(ctx, first, page);
    }
    const values = ctx.interaction.data?.values ?? [];
    if (action !== "choose" || !["user", "role"].includes(first ?? "") || !/^\d{15,20}$/u.test(second ?? "")
      || !["0", "1"].includes(preview ?? "") || !values.length || values.some(value => !refreshCategories.includes(value as RefreshCategory))) {
      throw new CommandInputError("Invalid refresh selection");
    }
    return runManualRefresh(ctx, first!, second!, preview === "1", values as RefreshCategory[], roleTreatment(treatment));
  };
  if (!waitUntil) return run();
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {})).catch(
    error => sendInteractionError(ctx,error,action!=="status"&&action!=="again")));
  return { type: (action==="status"||action==="again")?InteractionResponseType.DeferredUpdateMessage:InteractionResponseType.DeferredChannelMessageWithSource, data: {} };
}

export const mainAccountAction: Pick<Command, "autocomplete" | "execute"> = {
  async autocomplete(ctx) {
    const items = await ctx.services.api.get<{ items: Array<{ player_tag: string; hidden: boolean }> }>(`/v2/links/${invokingUserId(ctx)}`);
    const query = stringOption(ctx, "player")?.toUpperCase() ?? "";
    return items.items.filter(item => !item.hidden && item.player_tag.includes(query)).slice(0, 25).map(item => ({ name: item.player_tag, value: item.player_tag }));
  },
  async execute(ctx) {
    const guild = requireGuildId(ctx), actor = invokingUserId(ctx);
    const tag = stringOption(ctx, "player");
    if (!tag) throw new CommandInputError("Choose a visible linked account");
    const result = await ctx.services.api.post<{ tag: string }>(`/v2/bot/role-refresh/${guild}/main`, { actorId: actor, tag });
    const response = await runManualRefresh(ctx, "user", actor, false, ["nicknames"]);
    return { ...response, data: { ...response.data, content: `Main account for this server: ${result.tag}.\n${response.data?.content ?? ""}` } };
  },
};
