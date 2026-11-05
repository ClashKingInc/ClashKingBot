import { sendInteractionError } from "./errors";
import { actionRow, componentsV2, legacyMessage, linkButton, type ContainerChild } from "../discord/components";
import type { ApplicationEmojis } from "../discord/emojis";
import { InteractionResponseType, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError, invokingUserId, normalizeTag, requireGuildId } from "./command-utils";
import { emojis, escapeMarkdown, playerUrl } from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { CommandContext } from "./types";

export interface BanRecord {
  VillageTag?: string; VillageName?: string; DateCreated?: string; Notes?: string;
  tag?: string; player_name?: string; date_created?: string; reason?: string;
  name?: string; town_hall?: number; clan_name?: string; added_by?: string; image?: string;
}

export interface ModerationRecord extends BanRecord {
  kind?: "ban"|"strike";
  strike_id?: string;
  strike_weight?: number;
  rollover_date?: number;
}

function recordText(row: ModerationRecord, emoji: ApplicationEmojis, reasonLimit: number): string {
    const tag = row.tag ?? row.VillageTag ?? "";
    const name = row.name ?? row.player_name ?? row.VillageName ?? tag;
    const date = Date.parse(row.date_created ?? row.DateCreated ?? "");
    const addedBy = row.added_by && /^\d{15,22}$/u.test(row.added_by) ? `<@${row.added_by}>` : "Unknown";
    const rawReason = row.reason ?? row.Notes ?? "";
    const reason = rawReason.length > reasonLimit ? `${rawReason.slice(0,reasonLimit)}…` : rawReason;
    // Discord can expose bracket escapes inside masked-link labels. Keep
    // arbitrary player names outside the link and link the canonical tag.
    return `${emoji.get(row.town_hall ?? 0)} **${escapeMarkdown(name)}** ([${tag}](${playerUrl(tag)}))\n`
      + `${escapeMarkdown(row.clan_name ?? "No clan")}\n**Added by:** ${addedBy}`
      + (Number.isFinite(date) ? `\n**Added on:** <t:${Math.floor(date/1000)}:d> (<t:${Math.floor(date/1000)}:R>)` : "")
      + (row.kind === "strike" ? `\n**Weight:** ${row.strike_weight ?? 1}${row.rollover_date ? ` (expires <t:${row.rollover_date}:R>)` : ""}` : "")
      + `\n**Reason:** ${reason ? escapeMarkdown(reason) : "No reason provided"}`
      + (row.image ? ` ([image](${row.image}))` : "");
}

async function cards(ctx: CommandContext, rows: ModerationRecord[], heading: string | null, reasonLimit: number, controls: ContainerChild[] = [], showUnban = true, showImages = true, footer?: string) {
  const emoji = await emojis(ctx), server = requireGuildId(ctx);
  const content: ContainerChild[] = heading ? [{type:10,content:heading}] : [];
  rows.forEach((row,index) => {
    const tag = row.tag ?? row.VillageTag ?? "";
    const name = row.name ?? row.player_name ?? row.VillageName ?? tag;
    const text = (row.kind ? `**${row.kind === "ban" ? "Ban" : "Strike"}**\n` : "") + recordText(row, emoji, reasonLimit);
    if(index) content.push({type:14,divider:true,spacing:1});
    if(showUnban) content.push({type:9,components:[{type:10,content:text}],accessory: row.kind === "strike"
      ? {type:2,style:4,label:"Remove strike",custom_id:`ck:moderation:remove-strike:${server}:${row.strike_id}`}
      : {type:2,style:4,label:"Unban",custom_id:`ck:moderation:unban:${server}:${tag}`}});
    else content.push({type:10,content:text});
    if(showImages && row.image) content.push({type:12,items:[{media:{url:row.image},description:`Evidence for ${name}`} ]});
  });
  if(!rows.length) content.push({type:10,content:"No matching records."});
  if(footer) content.push({type:10,content:footer});
  const response = componentsV2([{type:17,accent_color:await serverEmbedColor(ctx),components:content}, ...controls]);
  response.data!.allowed_mentions = {parse:[]};
  return response;
}

export async function banListReply(ctx: CommandContext, requestedPage = 0) {
  const result = await ctx.services.api.get<{items:BanRecord[];count:number}>(`/v2/server/${requireGuildId(ctx)}/bans`);
  const timestamp = (row: BanRecord) => { const time = Date.parse(row.date_created ?? row.DateCreated ?? ""); return Number.isFinite(time) ? time : 0; };
  const rows = [...result.items].sort((a,b) => timestamp(b)-timestamp(a) || (a.tag ?? a.VillageTag ?? "").localeCompare(b.tag ?? b.VillageTag ?? ""));
  const emoji = await emojis(ctx);
  const pages: BanRecord[][] = [];
  let entries: BanRecord[] = [], characters = 0, components = 8;
  // Reserve heading/navigation space; count the same text that is rendered.
  // Each entry has a section, text and button, plus a separator after the first.
  // Pack against Discord's 4,000 text / 40 component limits, never a row limit.
  for (const row of rows) {
    const length = recordText(row,emoji,1000).length;
    const cost = entries.length ? 4 : 3;
    if (entries.length && (characters + length > 3650 || components + cost > 40)) {
      pages.push(entries); entries = []; characters = 0; components = 8;
    }
    components += entries.length ? 4 : 3;
    entries.push(row); characters += length;
  }
  if (entries.length || !pages.length) pages.push(entries);
  const last = pages.length-1, page = Math.min(last,Math.max(0,requestedPage));
  const id = (p:number) => `ck:moderation:banlist:${requireGuildId(ctx)}:${p}`;
  // A public list must not contain an actor-bound dashboard grant. The
  // regular route lets each visitor sign in with their own permissions.
  const dashboard = new URL("/dashboard/bans-and-strikes", ctx.env.DASHBOARD_BASE_URL);
  dashboard.searchParams.set("guildId", requireGuildId(ctx));
  const buttons = [
    ...(last ? [{type:2 as const,style:2 as const,label:"Previous",disabled:page===0,custom_id:id(page-1)}] : []),
    {type:2 as const,style:2 as const,emoji:emoji.component("refresh") ?? {name:"↻"},custom_id:id(page)},
    ...(last ? [{type:2 as const,style:2 as const,label:"Next",disabled:page===last,custom_id:id(page+1)}] : []),
    linkButton("Open dashboard", dashboard.toString()),
  ];
  return cards(ctx,pages[page]!,"## Ban List",1000,[actionRow(...buttons)],true,false,`-# ${result.count} ${result.count === 1 ? "ban" : "bans"}${last ? ` (Page ${page+1} of ${last+1})` : ""}`);
}

export async function banSavedReply(ctx: CommandContext, row: BanRecord) {
  return cards(ctx,[row],null,1000,[],false);
}

export async function moderationSavedReply(ctx:CommandContext,row:ModerationRecord,kind:"ban"|"strike") {
  return cards(ctx,[{...row,kind}],null,1000,[],false,true);
}

export async function moderationListReply(ctx:CommandContext,requestedPage=0,filter:"all"|"ban"|"strike"="all") {
  const server=requireGuildId(ctx);
  const kinds=filter==="all"?["ban","strike"] as const:[filter];
  const groups=await Promise.all(kinds.map(async kind=>{
    const {items}=await ctx.services.api.get<{items:ModerationRecord[]}>(`/v2/server/${server}/${kind==="ban"?"bans":"strikes"}`);
    return items.map(row=>({...row,kind}));
  }));
  const rows=groups.flat().sort((a,b)=>Date.parse(b.date_created??b.DateCreated??"")-Date.parse(a.date_created??a.DateCreated??""));
  const emoji=await emojis(ctx), pages:ModerationRecord[][]=[[]];
  // Seven entries reserve room for nested section buttons, the filter, and
  // navigation under Discord’s 40-component ceiling; text can split earlier.
  let size=0;
  for(const row of rows){
    const cost=recordText(row,emoji,1000).length+20;
    if(pages.at(-1)!.length&&(size+cost>3500||pages.at(-1)!.length>=7)){pages.push([]);size=0;}
    pages.at(-1)!.push(row);size+=cost;
  }
  const page=Math.min(pages.length-1,Math.max(0,requestedPage)),last=pages.length-1;
  const id=(p:number,f=filter)=>`ck:moderation:records:${server}:${f}:${p}`;
  const dashboard=new URL("/dashboard/bans-and-strikes",ctx.env.DASHBOARD_BASE_URL);dashboard.searchParams.set("guildId",server);
  const buttons=[...(last?[{type:2 as const,style:2 as const,label:"Previous",disabled:page===0,custom_id:id(page-1)},
    {type:2 as const,style:2 as const,label:`${page+1}/${pages.length}`,disabled:true,custom_id:`${id(page)}:count`}]:[]),
    {type:2 as const,style:2 as const,emoji:emoji.component("refresh")??{name:"↻"},custom_id:id(page)},
    ...(last?[{type:2 as const,style:2 as const,label:"Next",disabled:page===last,custom_id:id(page+1)}]:[]),linkButton("Open dashboard",dashboard.toString())];
  const count=`-# ${rows.length} ${filter==="all"?"records":filter==="ban"?(rows.length===1?"ban":"bans"):(rows.length===1?"strike":"strikes")}`;
  return cards(ctx,pages[page]!,filter==="ban"?"## Ban List":filter==="strike"?"## Strike List":"## Records",1000,[
    actionRow({type:3,custom_id:`ck:moderation:filter:${server}`,placeholder:"Record type",options:[{label:"All records",value:"all",default:filter==="all"},{label:"Bans",value:"ban",default:filter==="ban"},{label:"Strikes",value:"strike",default:filter==="strike"}]}),
    actionRow(...buttons)],true,false,count);
}

// The caller checks current Manage Server permissions before entering here.
// Public controls never trust the original message author's permission set.
export function dispatchBanRecord(ctx: CommandContext, waitUntil?: (promise:Promise<unknown>)=>void): DiscordInteractionResponse | Promise<DiscordInteractionResponse> | undefined {
  const parts = (ctx.interaction.data?.custom_id ?? "").split(":");
  const action = parts[2];
  if(action==="records"||action==="filter"||action==="remove-strike"||action==="confirm-strike"||action==="cancel-strike") {
    if(parts[3]!==requireGuildId(ctx))throw new CommandInputError("This list belongs to another server.");
    let task:()=>Promise<DiscordInteractionResponse>;
    if(action==="records"||action==="filter") {
      const filter=action==="filter"?ctx.interaction.data?.values?.[0]:parts[4];
      const page=action==="filter"?0:Number(parts[5]);
      if(!["all","ban","strike"].includes(filter??"")||!Number.isSafeInteger(page)||page<0)throw new CommandInputError("Choose a valid moderation page.");
      task=()=>moderationListReply(ctx,page,filter as "all"|"ban"|"strike");
    } else {
      const record=parts[4];
      if(!record||!/^[A-Za-z0-9_-]{1,20}$/u.test(record))throw new CommandInputError("Choose a valid strike.");
      if(action==="remove-strike")return legacyMessage({content:"Remove this strike?",components:[actionRow(
        {type:2,style:4,label:"Remove strike",custom_id:`ck:moderation:confirm-strike:${parts[3]}:${record}:${invokingUserId(ctx)}`},
        {type:2,style:2,label:"Cancel",custom_id:`ck:moderation:cancel-strike:${parts[3]}:${record}:${invokingUserId(ctx)}`})]},{ephemeral:true});
      if(parts[5]!==invokingUserId(ctx))throw new CommandInputError("This confirmation belongs to another user.");
      if(action==="cancel-strike")return {type:InteractionResponseType.UpdateMessage,data:{content:"Cancelled.",components:[]}};
      task=async()=>{await ctx.services.api.delete(`/v2/server/${requireGuildId(ctx)}/strikes/${encodeURIComponent(record)}`);return legacyMessage({content:"Strike removed.",components:[]},{ephemeral:true});};
    }
    if(!waitUntil)return task().then(reply=>({...reply,type:InteractionResponseType.UpdateMessage}));
    waitUntil(task().then(reply=>ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,reply.data!)).catch(error=>sendInteractionError(ctx,error,action==="confirm-strike")));
    return {type:InteractionResponseType.DeferredUpdateMessage};
  }

  if(!["banlist","unban","confirm-unban","cancel-unban"].includes(action ?? "")) return undefined;
  if(parts[3] !== requireGuildId(ctx)) throw new CommandInputError("This ban list belongs to another server.");
  if(action === "banlist") {
    if(parts.length!==5 || !/^\d{1,6}$/u.test(parts[4]!)) throw new CommandInputError("Invalid ban page.");
    const pending=banListReply(ctx,Number(parts[4]));
    if(!waitUntil)return pending.then(r=>({...r,type:InteractionResponseType.UpdateMessage}));
    waitUntil(pending.then(r=>ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,r.data!))
      .catch((error)=>sendInteractionError(ctx,error)));
    return {type:InteractionResponseType.DeferredUpdateMessage};
  }
  if(action === "unban") {
    if(parts.length!==5)throw new CommandInputError("Invalid unban control.");
    const tag=normalizeTag(parts[4]!,ctx.locale), actor=invokingUserId(ctx);
    return legacyMessage({content:`Remove the ban for **${tag}**?`,components:[actionRow(
      {type:2,style:4,label:"Unban",custom_id:`ck:moderation:confirm-unban:${parts[3]}:${actor}:${tag}`},
      {type:2,style:2,label:"Cancel",custom_id:`ck:moderation:cancel-unban:${parts[3]}:${actor}:${tag}`},
    )],allowed_mentions:{parse:[]}},{ephemeral:true});
  }
  if(parts.length!==6||parts[4]!==invokingUserId(ctx))throw new CommandInputError("This confirmation belongs to another user.");
  const tag=normalizeTag(parts[5]!,ctx.locale);
  if(action === "cancel-unban")return {type:InteractionResponseType.UpdateMessage,data:{content:"Cancelled.",components:[]}};
  const remove=async()=>{
    await ctx.services.api.delete(`/v2/server/${requireGuildId(ctx)}/bans/${encodeURIComponent(tag)}`);
    return legacyMessage({content:`Ban removed for **${tag}**.`,components:[],allowed_mentions:{parse:[]}},{ephemeral:true});
  };
  if(!waitUntil)return remove();
  waitUntil(remove().then(r=>ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,r.data!))
    .catch((error)=>sendInteractionError(ctx,error,true)));
  return {type:InteractionResponseType.DeferredUpdateMessage};
}
