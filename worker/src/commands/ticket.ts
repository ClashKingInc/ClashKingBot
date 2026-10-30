import { Schema } from "effect";
import { ApplicationEmojis } from "../discord/emojis";
import { ClashKingApiError } from "../api/client";
import { InteractionResponseType, InteractionType, MessageFlags, type DiscordInteraction, type DiscordInteractionResponse } from "../discord/types";
import { CommandInputError } from "./command-utils";
import type { Command, CommandServices } from "./types";

const uuid = "[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}";
const textField = Schema.Struct({ customId: Schema.String, label: Schema.String, required: Schema.Boolean,
  style: Schema.Literals(["short", "paragraph"]), maxLength: Schema.Number });
const option = Schema.Struct({ value: Schema.String, label: Schema.String, description: Schema.optional(Schema.String), townhall: Schema.optional(Schema.Number) });
const field = Schema.Union([textField, Schema.Struct({ customId:Schema.String,label:Schema.String,required:Schema.Boolean,
  style:Schema.Literal("select"),minValues:Schema.Number,maxValues:Schema.Number,options:Schema.Array(option) })]);
const modal = Schema.Struct({ kind: Schema.Literal("modal"), customId: Schema.String, title: Schema.String,
  fields: Schema.Array(field).check(Schema.isMinLength(1), Schema.isMaxLength(5)) });
const select = Schema.Struct({ kind: Schema.Literals(["account_select", "string_select"]), customId: Schema.String,
  content: Schema.String, placeholder: Schema.String, minValues: Schema.Number, maxValues: Schema.Number,
  options: Schema.Array(option).check(Schema.isMinLength(1), Schema.isMaxLength(25)) });
const form = Schema.Union([modal, select, Schema.Struct({ kind: Schema.Literal("continue"),
  customId: Schema.String, content: Schema.String, label: Schema.String })]);
const reply = Schema.Union([
  Schema.Struct({ outcome: Schema.Literals(["ready", "form"]), form }),
  Schema.Struct({ outcome: Schema.Literals(["accepted", "complete"]), operationId: Schema.String,
    state: Schema.Literals(["preparing", "submitted", "provisioning", "reconciling", "completed", "failed"]),
    channelId: Schema.optional(Schema.String) }),
  Schema.Struct({ outcome: Schema.Literal("link_required"), content: Schema.String,
    link: Schema.Struct({ customId: Schema.String, label: Schema.String }) }),
  Schema.Struct({ outcome: Schema.Literal("accounts"), content: Schema.String,
    select: Schema.Struct({ customId: Schema.String, placeholder: Schema.String,
      minValues: Schema.Number, maxValues: Schema.Number, options: Schema.Array(option) }) }),
  Schema.Struct({ outcome: Schema.Literals(["account", "linked"]), content: Schema.String }),
  Schema.Struct({ effectId: Schema.String, statusCustomId: Schema.String,
    state: Schema.Literals(["pending", "executing", "uncertain", "succeeded", "failed"]),
    messageId: Schema.optional(Schema.String) }),
  Schema.Struct({ operationId: Schema.String,
    state: Schema.Literals(["preparing", "submitted", "provisioning", "reconciling", "completed", "failed"]),
    result: Schema.optional(Schema.Unknown) }),
]);

export const ticketCommand: Command = {
  definition: {
    name: "ticket", description: "Update the current ticket", type: 1,
    contexts: [0], integration_types: [0],
    options: [
      { name: "status", description: "Change this ticket's status", type: 1,
        options: [{ name: "status", description: "Ticket status", type: 3, required: true,
          choices: ["open", "sleep", "close"].map(value => ({ name: value, value })) }] },
      { name: "add", description: "Add a member to this ticket", type: 1,
        options: [{ name: "member", description: "Server member", type: 6, required: true }] },
    ],
  },
  async execute() {
    throw new CommandInputError("Ticket actions require the original signed Discord interaction.");
  },
};

export interface TicketInteractionProof { readonly rawBody: string; readonly timestamp: string; readonly signature: string }

// Forms must be answered immediately: Discord cannot open a modal from a deferred response.
// API authorization derives every input from these exact signed bytes, never unsigned Bot fields.
export async function ticketInteraction(interaction: DiscordInteraction, proof: TicketInteractionProof,
  services: CommandServices, background?: (promise: Promise<unknown>) => void): Promise<DiscordInteractionResponse> {
  const path = ticketPath(interaction);
  if (!interaction.guild_id || !path) return privateMessage("This ticket control is invalid.");
  try {
    const [raw, emojis] = await Promise.all([
      services.api.post<unknown>(path, { interaction: proof }),
      path.endsWith("/open/prepare") ? services.discordRest.listApplicationEmojis(AbortSignal.timeout(1200)).catch(() => []) : Promise.resolve([]),
    ]);
    const result = Schema.decodeUnknownSync(reply)(raw);
    if (background && "state" in result && !["completed", "succeeded", "failed"].includes(result.state)) {
      background(updateTicketProgress(interaction, proof, path, services));
    }
    return ticketReply(result, interaction.guild_id, interaction.channel_id, emojis);
  } catch (error) {
    let content = "Couldn't process this ticket action. Please try again.";
    if (error instanceof ClashKingApiError && [400, 403, 404, 409, 429].includes(error.status)) {
      try {
        const body: unknown = JSON.parse(error.body);
        if (typeof body === "object" && body !== null && "message" in body && typeof body.message === "string") {
          content = body.message.slice(0, 500);
        }
      } catch { /* Never expose provider errors or credentials. */ }
    }
    return privateMessage(content);
  }
}

// Replay the identical signed request: API replay receipts return current state without
// repeating the action. Never manufacture a status interaction or weaken its proof.
async function updateTicketProgress(interaction: DiscordInteraction, proof: TicketInteractionProof,
  path: string, services: CommandServices): Promise<void> {
  try {
    for (let attempt = 0; attempt < 12; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const result = Schema.decodeUnknownSync(reply)(await services.api.post<unknown>(path, { interaction: proof }));
      if (!("state" in result) || !["completed", "succeeded", "failed"].includes(result.state)) continue;
      const response = ticketReply(result, interaction.guild_id!, interaction.channel_id);
      if (response.data) await services.discordRest.editOriginalInteractionResponse(interaction.token, response.data);
      return;
    }
    await services.discordRest.editOriginalInteractionResponse(interaction.token, {
      content: "This ticket action is still processing. You can dismiss this message; its progress is available in the dashboard.",
      components: [], allowed_mentions: { parse: [] },
    });
  } catch { /* A dismissed response or temporary outage must not repeat the action. */ }
}

export function ticketPath(interaction: DiscordInteraction): string | undefined {
  const base = "/v2/runtime";
  if (interaction.type === InteractionType.ApplicationCommand && interaction.data?.name === "ticket") {
    // Old cached slash definitions must not publish setup panels after removal.
    return ["status", "add"].includes(interaction.data.options?.[0]?.name ?? "")
      ? `${base}/tickets/actions` : undefined;
  }
  if (interaction.type !== InteractionType.MessageComponent && interaction.type !== InteractionType.ModalSubmit) return undefined;
  const id = interaction.data?.custom_id ?? "";
  if (interaction.type === InteractionType.MessageComponent && /^.{1,75}_(?:0|\d{10})$/u.test(id)) return `${base}/tickets/open/prepare`;
  if (new RegExp(`^ck:ticket:open:${uuid}:${uuid}$`, "iu").test(id)) return `${base}/tickets/open/prepare`;
  if (new RegExp(`^ck:ticket:menu:${uuid}:[0-9a-z-]+$`, "iu").test(id)) return `${base}/tickets/open/prepare`;
  if (new RegExp(`^ck:ticket:(accounts-view|account-view|link|link-submit):${uuid}$`, "iu").test(id)) return `${base}/tickets/accounts`;
  if (new RegExp(`^ck:ticket:(close|delete|assign|approve):${uuid}$`, "iu").test(id)) return `${base}/tickets/actions`;
  const advance = new RegExp(`^ck:ticket:(accounts|select|continue|answers):(${uuid})(?::[0-9]+)?$`, "iu").exec(id);
  if (advance) return `${base}/ticket-operations/${advance[2]}/advance`;
  const status = new RegExp(`^ck:ticket:status:(${uuid})$`, "iu").exec(id);
  if (status) return `${base}/ticket-operations/${status[1]}/status`;
  const publication = /^ck:ticket:panel-status:([0-9a-f]{64})$/iu.exec(id);
  return publication ? `${base}/ticket-panel-publications/${publication[1]}/status` : undefined;
}

const button = (custom_id: string, label: string) => [{ type: 1, components: [{ type: 2, style: 2, custom_id, label }] }];
const privateMessage = (content: string, components: unknown[] = []): DiscordInteractionResponse => ({
  type: InteractionResponseType.ChannelMessageWithSource,
  data: { content, components, flags: MessageFlags.Ephemeral, allowed_mentions: { parse: [] } },
});

function ticketReply(result: typeof reply.Type, guild: string, channel?: string,
  emojis: readonly {id: string; name: string; animated?: boolean}[] = []): DiscordInteractionResponse {
  if ("form" in result) {
    const value = result.form;
    if (value.kind === "modal") return { type: InteractionResponseType.Modal,
      data: { custom_id: value.customId, title: value.title, components: value.fields.map(input => ({
        type: 18, label: input.label, component: input.style === "select"
          ? { type:3,custom_id:input.customId,required:input.required,min_values:input.minValues,max_values:input.maxValues,
            options:input.options.map(({townhall,...item}) => {
              const emoji = new ApplicationEmojis(emojis).component(`th${townhall}`);
              return {...item,...(emoji ? {emoji:{id:emoji.id,name:emoji.name,animated:emoji.animated ?? false}} : {})};
            }) }
          : { type:4,custom_id:input.customId,required:input.required,style:input.style === "paragraph" ? 2 : 1,max_length:input.maxLength },
      })) } };
    if (value.kind === "continue") return privateMessage(value.content, button(value.customId, value.label));
    return privateMessage(value.content, selectComponents(value));
  }
  // The existing /link flow owns account verification and role evaluation.
  // Do not show the archived ticket-link modal, whose submission is disabled.
  if ("link" in result) return privateMessage(`${result.content}\nUse /link to link your account, then click the panel button again.`);
  if ("select" in result) return privateMessage(result.content, selectComponents(result.select));
  if ("content" in result) return privateMessage(result.content);
  if ("effectId" in result) {
    if (result.state === "succeeded" && result.messageId && channel) {
      return privateMessage(`[Ticket panel posted](https://discord.com/channels/${guild}/${channel}/${result.messageId}).`);
    }
    return privateMessage(result.state === "failed" ? "Ticket panel couldn't be posted." : "Posting your ticket panel…");
  }
  if (result.state === "completed") {
    const stored = "result" in result ? result.result : undefined;
    const channelId = "channelId" in result && typeof result.channelId === "string" ? result.channelId
      : typeof stored === "object" && stored !== null && "channelId" in stored && typeof stored.channelId === "string"
        ? stored.channelId : undefined;
    return privateMessage(channelId && /^\d{1,20}$/u.test(channelId)
      ? `Your ticket is ready: [Open ticket](https://discord.com/channels/${guild}/${channelId}).` : "Ticket updated.");
  }
  return privateMessage(result.state === "failed" ? "This ticket action failed. Contact your server staff."
    : "Processing your ticket…");
}

function selectComponents(value: { customId: string; placeholder: string; minValues: number; maxValues: number;
  options: ReadonlyArray<{ value: string; label: string; description?: string }> }) {
  return [{ type: 1, components: [{ type: 3, custom_id: value.customId, placeholder: value.placeholder,
    min_values: value.minValues, max_values: value.maxValues, options: value.options }] }];
}
