import { ClashKingApiError } from "../api/client";
import { InteractionResponseType, MessageFlags, type DiscordInteraction, type DiscordInteractionResponse } from "../discord/types";
import { dashboardCommand } from "./dashboard";
import { legacyMessage } from "../discord/components";
import { CommandInputError, requireGuildId } from "./command-utils";
import type { Command, CommandContext, CommandServices } from "./types";

export interface GiveawayInteractionProof {
  rawBody: string;
  timestamp: string;
  signature: string;
}

/** Forward the original Discord-signed request; the API owns eligibility and atomic entry receipts. */
export function giveawayEntry(
  interaction: DiscordInteraction,
  proof: GiveawayInteractionProof,
  services: CommandServices,
  waitUntil: (promise: Promise<unknown>) => void,
): DiscordInteractionResponse {
  const id = /^ck:giveaway:enter:([0-9a-f-]{36})$/i.exec(interaction.data?.custom_id ?? "")?.[1];
  if (!id || !interaction.guild_id || !interaction.message?.id || interaction.type !== 3 || interaction.data?.component_type !== 2) {
    return { type: InteractionResponseType.ChannelMessageWithSource, data: { flags: MessageFlags.Ephemeral, content: "This giveaway button is invalid." } };
  }
  waitUntil(completeEntry(interaction, id, proof, services));
  return { type: InteractionResponseType.DeferredChannelMessageWithSource, data: { flags: MessageFlags.Ephemeral } };
}

async function completeEntry(interaction: DiscordInteraction, id: string, proof: GiveawayInteractionProof, services: CommandServices): Promise<void> {
  let content: string;
  try {
    const result = await services.api.post<{ outcome: "entered" | "already_entered" }>(`/v2/runtime/giveaways/${id}/entries`, { interaction: proof });
    content = result.outcome === "entered" ? "You successfully joined the giveaway! 🎉" : "You already joined this giveaway.";
  } catch (error) {
    content = "The giveaway couldn't be joined right now. Please try again.";
    if (error instanceof ClashKingApiError && [400, 403, 404, 409].includes(error.status)) {
      try {
        const body: unknown = JSON.parse(error.body);
        if (typeof body === "object" && body !== null && "message" in body && typeof body.message === "string") content = body.message.slice(0, 500);
      } catch { /* Keep the safe retry message. */ }
    }
  }
  await services.discordRest.editOriginalInteractionResponse(interaction.token, { content, flags: MessageFlags.Ephemeral });
}

interface GiveawaySummary { id: string; prize: string; end: string; disabled?: boolean }
const giveawayId = /^[A-Za-z0-9_-]{1,80}$/u;
function requireManager(ctx: CommandContext) {
 const permissions=ctx.interaction.member?.permissions??"0";
 if(!/^\d+$/u.test(permissions)||(BigInt(permissions)&(8n|32n))===0n)throw new CommandInputError("Manage Server permission is required.");
}
export const giveawayCommand: Command = {
 deferred:true,ephemeral:true,
 definition:{name:"giveaway",type:1,description:"Manage giveaway winners and open the dashboard",contexts:[0],integration_types:[0],default_member_permissions:"32",options:[
  {name:"reroll",type:1,description:"Replace selected winners of an ended giveaway",options:[
   {name:"giveaway",type:3,description:"Ended giveaway",required:true,autocomplete:true},
   {name:"winners",type:3,description:"Mentions or IDs of current winners to replace (up to 25)",required:true,max_length:600},
   {name:"reason",type:3,description:"Reason shown with the reroll",max_length:1000},
  ]},
  {name:"dashboard",type:1,description:"Open this server's giveaway dashboard"},
 ]},
 async autocomplete(ctx) {
  requireManager(ctx);
  const focused=ctx.interaction.data?.options?.[0]?.options?.find(option=>option.focused);
  if(focused?.name!=="giveaway")return [];
  const query=String(focused.value??"").toLocaleLowerCase();
  const result=await ctx.services.api.get<{ended:GiveawaySummary[]}>(`/v2/server/${requireGuildId(ctx)}/giveaways`,{},AbortSignal.timeout(1500));
  return result.ended.filter(item=>!item.disabled&&giveawayId.test(item.id)&&`${item.prize} ${item.id}`.toLocaleLowerCase().includes(query))
   .slice(0,25).map(item=>({name:`${item.prize} · ${item.end.slice(0,10)}`.slice(0,100),value:item.id}));
 },
 async execute(ctx) {
  requireManager(ctx);const server=requireGuildId(ctx),sub=ctx.interaction.data?.options?.[0];
  if(sub?.name==="dashboard")return dashboardCommand.execute(ctx);
  if(sub?.name!=="reroll")throw new CommandInputError("Choose a giveaway action.");
  const options=new Map(sub.options?.map(option=>[option.name,option.value]));
  const id=String(options.get("giveaway")??"");
  if(!giveawayId.test(id))throw new CommandInputError("Choose an ended giveaway from autocomplete.");
  const values=String(options.get("winners")??"").split(/[\s,]+/u).filter(Boolean);
  const users=values.map(value=>/^<@!?(\d{15,20})>$/u.exec(value)?.[1]??value);
  if(!users.length||users.length>25||users.some(user=>!/^\d{15,20}$/u.test(user))||new Set(users).size!==users.length)throw new CommandInputError("Enter 1–25 distinct winner mentions or Discord IDs.");
  try {
   const result=await ctx.services.api.post<{newWinners:string[]}>(`/v2/server/${server}/giveaways/${id}/reroll`,{user_ids_to_replace:users,reason:String(options.get("reason")??"")});
   // No repeat button: a reroll changes the authoritative winners and must not
   // be retried after an uncertain response without checking their current state.
   return legacyMessage({content:`Replaced ${users.length} winner(s). New winners: ${result.newWinners.map(user=>`<@${user}>`).join(", ")}. The announcement uses the giveaway's normal delivery flow.`,allowed_mentions:{parse:[]}},{ephemeral:true});
  } catch(error) {
   if(error instanceof ClashKingApiError&&[400,403,404,409].includes(error.status)) {
    try {const body=JSON.parse(error.body) as {message?:unknown};if(typeof body.message==="string")throw new CommandInputError(body.message.slice(0,1000));}catch(parsed){if(parsed instanceof CommandInputError)throw parsed;}
   }
   throw new CommandInputError("The reroll could not be confirmed. Check the current winners in the dashboard before trying again.");
  }
 }
};
