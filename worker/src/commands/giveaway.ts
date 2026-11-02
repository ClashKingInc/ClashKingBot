import { CommandInputError } from "./command-utils";
import { interactionErrorReply, sendInteractionError } from "./errors";
import { InteractionResponseType, MessageFlags, type DiscordInteraction, type DiscordInteractionResponse } from "../discord/types";
import type { CommandServices } from "./types";

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
    return interactionErrorReply(new CommandInputError("This giveaway button is invalid."),interaction);
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
    await sendInteractionError({interaction,services},error,true);
    return;
  }
  await services.discordRest.editOriginalInteractionResponse(interaction.token, { content, flags: MessageFlags.Ephemeral });
}
