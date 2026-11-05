import { modalFields, textField } from "./modals";
import { sendInteractionError } from "./errors";
import { legacyMessage } from "../discord/components";
import {
  InteractionResponseType,
  InteractionType,
  type DiscordInteractionResponse,
} from "../discord/types";
import {
  CommandInputError,
  invokingUserId,
  normalizeTag,
  OptionType,
  requireGuildId,
  stringOption,
} from "./command-utils";
import {
  subcommand,
} from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { Command, CommandContext } from "./types";
import { moderationListReply, moderationSavedReply, banSavedReply, dispatchBanRecord, type BanRecord, type ModerationRecord } from "./ban-records";
import { ClashKingApiError } from "../api/client";

type Kind = "ban" | "strike";
function authorize(ctx: CommandContext) {
  requireGuildId(ctx);
  const permissions = ctx.interaction.member?.permissions ?? "0";
  if (!/^\d+$/u.test(permissions) || (BigInt(permissions) & (8n | 32n)) === 0n)
    throw new CommandInputError(
      "Manage Server permission is required for moderation records.",
    );
}
const kindOption = { name: "type", description: "Ban or strike", type: OptionType.String,
  required: true, choices: [{name:"Ban",value:"ban"},{name:"Strike",value:"strike"}] };
export const moderationCommand: Command = {
  deferred: context => subcommand(context).path[0] !== "add",
  ephemeral: context => subcommand(context).path[0] === "remove",
  definition: {name:"record",description:"Manage player bans and strikes",type:1,contexts:[0],integration_types:[0],default_member_permissions:"32",options:[
    {name:"add",description:"Add a player ban or strike",type:OptionType.Subcommand,options:[
      {name:"player_tag",description:"Clash of Clans player tag",type:OptionType.String,required:true}, kindOption]},
    {name:"list",description:"View bans and strikes",type:OptionType.Subcommand,options:[{...kindOption,required:false}]},
    {name:"remove",description:"Remove a ban or strike",type:OptionType.Subcommand,options:[kindOption,
      {name:"record",description:"Choose an existing record",type:OptionType.String,required:true,autocomplete:true}]},
  ]},
  async autocomplete(context) {
    const ctx=subcommand(context); authorize(ctx);
    const kind=stringOption(ctx,"type");
    if(!isKind(kind)||ctx.path[0]!=="remove")return [];
    const {items}=await ctx.services.api.get<{items:ModerationRecord[]}>(`/v2/server/${requireGuildId(ctx)}/${kind==="ban"?"bans":"strikes"}`);
    const query=(stringOption(ctx,"record")??"").toLocaleLowerCase();
    return items.map(row=>({name:`${row.name??row.player_name??row.VillageName??row.tag} (${row.tag??row.VillageTag})${row.strike_id?` [${row.strike_id}]`:""}`.slice(0,100),value:kind==="ban"?(row.tag??row.VillageTag??""):(row.strike_id??"")}))
      .filter(item=>item.value&&item.name.toLocaleLowerCase().includes(query)).slice(0,25);
  },
  async execute(context) {
    const ctx=subcommand(context); authorize(ctx);
    const kind=stringOption(ctx,"type");
    if(ctx.path[0]==="list")return moderationListReply(ctx,0,isKind(kind)?kind:"all");
    if(!isKind(kind))throw new CommandInputError("Choose Ban or Strike.");
    if(ctx.path[0]==="add")return moderationForm(ctx,kind);
    if(ctx.path[0]==="remove") {
      const id=stringOption(ctx,"record")??"";
      if(kind==="ban")normalizeTag(id,ctx.locale);
      else if(!/^[A-Za-z0-9_-]{1,20}$/u.test(id))throw new CommandInputError("Choose a valid strike.");
      await ctx.services.api.delete(`/v2/server/${requireGuildId(ctx)}/${kind==="ban"?"bans":"strikes"}/${encodeURIComponent(id)}`);
      return legacyMessage({embeds:[{description:`${kind==="ban"?"Ban":"Strike"} removed.`,color:await serverEmbedColor(ctx)}]},{ephemeral:true});
    }
    throw new CommandInputError("Choose add, list or remove.");
  },
};
function isKind(value:string|undefined):value is Kind{return value==="ban"||value==="strike";}
function moderationForm(ctx:CommandContext,kind:Kind):DiscordInteractionResponse {
  const tag=normalizeTag(stringOption(ctx,"player_tag")??"",ctx.locale);
  const optionalField=(id:string,label:string,placeholder:string)=>({type:18,label,component:{type:4,custom_id:id,style:1,required:false,max_length:4,placeholder}});
  return {type:InteractionResponseType.Modal,data:{title:`${kind==="ban"?"Ban":"Strike"} ${tag}`,
    custom_id:`ck:moderation:submit:${requireGuildId(ctx)}:${invokingUserId(ctx)}:${kind}:${tag}`,
    components:[textField("reason","Reason",1000,true),
      ...(kind==="strike"?[optionalField("weight","Strike weight","1"),optionalField("expires_in","Expires after (days)","Leave blank for no expiry")]:[]),
      {type:18,label:"Evidence image (optional)",description:"PNG, JPEG, GIF or WebP up to 10 MB",component:{type:19,custom_id:"image",required:false,min_values:0,max_values:1,file_types:[".png",".jpg",".jpeg",".gif",".webp"]}},
    ]}};
}

async function executeModeration(
  ctx: CommandContext,
  kind: Kind,
): Promise<DiscordInteractionResponse> {
  const server = requireGuildId(ctx),
    base = `/v2/server/${server}/${kind === "ban" ? "bans" : "strikes"}`,
    action = ctx.path[0];
  if (action !== "add")
    throw new CommandInputError("Choose add, remove or list.");
  const tag = normalizeTag(stringOption(ctx, "player_tag") ?? "", ctx.locale),
    reason = stringOption(ctx, "reason");
  if (!reason || reason.length > 1000)
    throw new CommandInputError("Enter a reason of up to 1,000 characters.");
  if (kind === "ban") {
    const existing = await ctx.services.api.get<{items:BanRecord[]}>(base);
    if (existing.items.some(row => (row.tag ?? row.VillageTag) === tag))
      throw new CommandInputError(`${tag} is already banned.`);
  }
  const weight = Number(ctx.options.get("weight")?.value ?? 1),
    days = Number(ctx.options.get("expires_in")?.value ?? 0);
  if (
    kind === "strike" &&
    (!Number.isSafeInteger(weight) ||
      weight < 1 ||
      weight > 100 ||
      !Number.isSafeInteger(days) ||
      days < 0 ||
      days > 3650)
  )
    throw new CommandInputError(
      "Choose a weight from 1 to 100 and expiry up to 3,650 days.",
    );
  let image: string | null = null;
  const attachmentId = stringOption(ctx, "image");
  if (attachmentId) {
    const attachment =
      ctx.interaction.data?.resolved?.attachments?.[attachmentId];
    if (
      !attachment ||
      attachment.size <= 0 ||
      attachment.size > 10 * 1024 * 1024 ||
      !["image/png", "image/jpeg", "image/gif", "image/webp"].includes(
        attachment.content_type ?? "",
      ) ||
      !/\.(png|jpe?g|gif|webp)$/iu.test(attachment.filename)
    )
      throw new CommandInputError(
        "Choose a PNG, JPEG, GIF or WebP image up to 10 MB.",
      );
    const bytes = await ctx.services.discordRest.download(
        attachment.url,
        10 * 1024 * 1024,
      ),
      form = new FormData();
    form.set("file", bytes, attachment.filename);
    image = (
      await ctx.services.api.postForm<{ url: string }>(
        "/v2/bot/moderation/images",
        form,
      )
    ).url;
  }
  const body =
    kind === "ban"
      ? { reason, added_by: invokingUserId(ctx), image }
      : {
          reason,
          added_by: invokingUserId(ctx),
          image: image ?? "",
          strike_weight: weight,
          rollover_days: days,
        };
  const result = await (kind === "ban"
    ? ctx.services.api.postIfAbsent<{strike_id?:string;player_name?:string}>(`${base}/${encodeURIComponent(tag)}`, body)
    : ctx.services.api.post<{strike_id?:string;player_name?:string}>(`${base}/${encodeURIComponent(tag)}`, body)
  ).catch(error => {
    if (kind === "ban" && error instanceof ClashKingApiError && error.status === 409)
      throw new CommandInputError(`${tag} is already banned.`);
    throw error;
  });
  if (kind === "ban") {
    // The mutation has already succeeded. Optional display enrichment must
    // never turn that success into a failure that encourages duplicate writes.
    const saved = await ctx.services.api.get<{items:BanRecord[]}>(base)
      .then(value => value.items.find(row => (row.tag ?? row.VillageTag) === tag))
      .catch(() => undefined);
    return banSavedReply(ctx, saved ?? {tag,player_name:result.player_name,reason,
      added_by:invokingUserId(ctx),date_created:new Date().toISOString(),...(image?{image}:{})});
  }
  const saved=await ctx.services.api.get<{items:ModerationRecord[]}>(base)
    .then(value=>value.items.find(row=>row.strike_id===result.strike_id)).catch(()=>undefined);
  return moderationSavedReply(ctx,saved??{tag,player_name:result.player_name,reason,added_by:invokingUserId(ctx),date_created:new Date().toISOString(),strike_id:result.strike_id,strike_weight:weight,...(days?{rollover_date:Math.floor(Date.now()/1000)+days*86400}:{}),...(image?{image}:{})},"strike");
}

export function dispatchModeration(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> | DiscordInteractionResponse {
  authorize(ctx);
  const record=dispatchBanRecord(ctx,waitUntil);
  if(record)return record;
  const match=/^ck:moderation:submit:([0-9]{15,22}):([0-9]{15,22}):(ban|strike):(#[0289PYLQGRJCUV]+)$/u.exec(ctx.interaction.data?.custom_id??"");
  if(!match||match[1]!==requireGuildId(ctx)||match[2]!==invokingUserId(ctx)||ctx.interaction.type!==InteractionType.ModalSubmit)
    throw new CommandInputError("Open a new record form with /record add.");
  const fields=modalFields(ctx.interaction.data?.components),options=new Map(ctx.options);
  options.set("player_tag",{name:"player_tag",type:OptionType.String,value:match[4]!});
  for(const name of ["reason","weight","expires_in"]) {
    const value=fields.get(name)?.value?.trim();
    if(value)options.set(name,{name,type:OptionType.String,value});
  }
  const images=fields.get("image")?.values??[];
  if(images.length>1)throw new CommandInputError("Choose one evidence image.");
  if(images[0])options.set("image",{name:"image",type:OptionType.Attachment,value:images[0]});
  const run=()=>executeModeration({...ctx,path:["add"],options},match[3] as Kind);
  if(!waitUntil)return run();
  waitUntil(run().then(reply=>ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token,reply.data??{})).catch(error=>sendInteractionError(ctx,error,true)));
  return {type:InteractionResponseType.DeferredChannelMessageWithSource};
}
