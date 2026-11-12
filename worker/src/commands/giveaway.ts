import { editOriginalInteractionResponse } from "../discord/message-actions";
import { CommandInputError } from "./command-utils";
import { interactionErrorReply, sendInteractionError } from "./errors";
import { ClashKingApiError } from "../api/client";
import { actionRow, type ActionRowComponent } from "../discord/components";
import { InteractionResponseType, MessageFlags, type DiscordInteraction, type DiscordInteractionResponse } from "../discord/types";
import type { CommandServices } from "./types";

export interface GiveawayInteractionProof {
  rawBody: string;
  timestamp: string;
  signature: string;
}
interface Participation {
  outcome: "entered" | "already_entered" | "left" | "already_left";
  canLeave?: boolean;
}

/** Forward the original Discord-signed request; the API owns membership and replay protection. */
export function giveawayEntry(
  interaction: DiscordInteraction,
  proof: GiveawayInteractionProof,
  services: CommandServices,
  waitUntil: (promise: Promise<unknown>) => void,
): DiscordInteractionResponse {
  const match = /^ck:giveaway:(enter|leave):([0-9a-f-]{36})(?::([0-9]{1,20}))?$/i.exec(interaction.data?.custom_id ?? "");
  const action = match?.[1];
  const id = match?.[2];
  if (!id || !interaction.guild_id || !interaction.message?.id || interaction.type !== 3 || interaction.data?.component_type !== 2 ||
    (action === "leave") !== Boolean(match?.[3])) {
    return interactionErrorReply(new CommandInputError("This giveaway button is invalid."), interaction);
  }
  waitUntil(completeEntry(interaction, id, action === "leave", proof, services));
  // Leave edits the private confirmation in place; the public giveaway stays intact.
  return action === "leave" ? { type: InteractionResponseType.DeferredUpdateMessage } :
    { type: InteractionResponseType.DeferredChannelMessageWithSource, data: { flags: MessageFlags.Ephemeral } };
}

async function completeEntry(interaction: DiscordInteraction, id: string, leaving: boolean, proof: GiveawayInteractionProof, services: CommandServices): Promise<void> {
  let content: string;
  let components: ActionRowComponent[] = [];
  try {
    const result = await services.api.post<Participation>(`/v2/runtime/giveaways/${id}/entries`, { interaction: proof });
    switch (result.outcome) {
      case "entered": content = "You’re entered! 🎉"; break;
      case "already_entered": content = result.canLeave === false ? "You’re already entered. Entries are now closed." : "You’re already entered."; break;
      case "left": content = "You’ve left the giveaway."; break;
      case "already_left": content = "You’re not entered in this giveaway."; break;
    }
    if (!leaving && result.canLeave === true) {
      components = [actionRow({ type: 2, style: 2, label: "Leave giveaway", custom_id: `ck:giveaway:leave:${id}:${interaction.message!.id}` })];
    }
  } catch (error) {
    // Closed giveaways are an expected state, not a stale-list error. Do not
    // misclassify other conflicts (identity mismatch/replay) as membership.
    let closed = false;
    if (error instanceof ClashKingApiError && error.status === 409) {
      try { closed = (JSON.parse(error.body) as { reason?: string }).reason === "not_open"; } catch { /* Retain the canonical error handling for malformed responses. */ }
    }
    if (!closed) { await sendInteractionError({ interaction, services }, error, true); return; }
    content = leaving ? "Entries are closed, so you can’t leave this giveaway now." : "This giveaway is no longer accepting entries.";
  }
  await editOriginalInteractionResponse(services.discordRest,interaction.token,{
    content, components, embeds: [], flags: MessageFlags.Ephemeral,
  });
}
