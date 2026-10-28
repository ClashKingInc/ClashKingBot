import { actionRow, legacyMessage } from "../discord/components";
import {
  InteractionResponseType,
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
  emojis,
  escapeMarkdown,
  playerAutocomplete,
  playerOption,
  subcommand,
} from "./game-common";
import { serverEmbedColor } from "./embed-color";
import type { Command, CommandContext } from "./types";

type Kind = "ban" | "strike";
interface RecordRow {
  VillageTag?: string;
  VillageName?: string;
  Notes?: string;
  tag?: string;
  player_name?: string;
  reason?: string;
  strike_id?: string;
  strike_weight?: number;
  image?: string;
  DateCreated?: string;
  date_created?: string;
}
function authorize(ctx: CommandContext) {
  requireGuildId(ctx);
  const permissions = ctx.interaction.member?.permissions ?? "0";
  if (!/^\d+$/u.test(permissions) || (BigInt(permissions) & (8n | 32n)) === 0n)
    throw new CommandInputError(
      "Manage Server permission is required for moderation records.",
    );
}
const reasonOption = {
  name: "reason",
  description: "Reason for this moderation record",
  type: OptionType.String,
  required: true,
  min_length: 1,
  max_length: 1000,
};
function command(kind: Kind): Command {
  return {
    deferred: true,
    ephemeral: true,
    definition: {
      name: kind,
      description: `Manage this server's ${kind} records`,
      type: 1,
      contexts: [0],
      integration_types: [0],
      default_member_permissions: "32",
      options: [
        {
          name: "add",
          description: `Add ${kind === "ban" ? "or update a ban" : "a strike"} for a player`,
          type: OptionType.Subcommand,
          options: [
            playerOption,
            reasonOption,
            ...(kind === "strike"
              ? [
                  {
                    name: "weight",
                    description: "Strike weight (default 1)",
                    type: OptionType.Integer,
                    min_value: 1,
                    max_value: 100,
                  },
                  {
                    name: "expires_in",
                    description: "Days until expiry; omit for no expiry",
                    type: OptionType.Integer,
                    min_value: 1,
                    max_value: 3650,
                  },
                ]
              : []),
            {
              name: "image",
              description: "Optional evidence image, up to 10 MB",
              type: OptionType.Attachment,
            },
          ],
        },
        {
          name: "remove",
          description: `Remove a ${kind} record`,
          type: OptionType.Subcommand,
          options: [
            kind === "ban"
              ? playerOption
              : {
                  name: "strike_id",
                  description: "Strike ID shown in the list",
                  type: OptionType.String,
                  required: true,
                  max_length: 20,
                },
          ],
        },
        {
          name: "list",
          description: `View this server's ${kind} records`,
          type: OptionType.Subcommand,
          options: [
            {
              name: "limit",
              description: "Records to show (default 20)",
              type: OptionType.Integer,
              min_value: 1,
              max_value: 50,
            },
            ...(kind === "strike"
              ? [
                  { ...playerOption, required: false },
                  {
                    name: "expired",
                    description: "Include expired strikes",
                    type: OptionType.Boolean,
                  },
                ]
              : []),
          ],
        },
      ],
    },
    async autocomplete(context) {
      authorize(context);
      return playerAutocomplete(context);
    },
    async execute(context) {
      const ctx = subcommand(context);
      authorize(ctx);
      return executeModeration(ctx, kind);
    },
  };
}
export const banCommand = command("ban"),
  strikeCommand = command("strike");

async function executeModeration(
  ctx: CommandContext,
  kind: Kind,
): Promise<DiscordInteractionResponse> {
  const server = requireGuildId(ctx),
    base = `/v2/server/${server}/${kind === "ban" ? "bans" : "strikes"}`,
    action = ctx.path[0];
  if (action === "list") {
    const limit = Number(ctx.options.get("limit")?.value ?? 20),
      filter = stringOption(ctx, "player"),
      expired = ctx.options.get("expired")?.value === true;
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 50)
      throw new CommandInputError("Choose a limit from 1 to 50.");
    const result = await ctx.services.api.get<{
      items: RecordRow[];
      count: number;
    }>(
      base,
      kind === "strike"
        ? {
            ...(filter ? { player_tag: normalizeTag(filter, ctx.locale) } : {}),
            view_expired: expired,
          }
        : {},
    );
    const emoji = await emojis(ctx);
    let description = "",
      shown = 0;
    const rows = [...result.items].sort((a, b) =>
      (b.date_created ?? b.DateCreated ?? "").localeCompare(
        a.date_created ?? a.DateCreated ?? "",
      ),
    );
    for (const row of rows.slice(0, limit)) {
      const line = `**${escapeMarkdown(row.player_name ?? row.VillageName ?? row.tag ?? row.VillageTag ?? "Player")}** · ${row.tag ?? row.VillageTag ?? ""}${row.strike_id ? ` · ID: \`${row.strike_id}\` · weight ${row.strike_weight ?? 1}` : ""}\n${escapeMarkdown(row.reason ?? row.Notes ?? "No reason").slice(0, 200)}`;
      if (description.length + line.length + 2 > 3500) break;
      description += (description ? "\n\n" : "") + line;
      shown++;
    }
    const id = [
      "ck",
      "moderation",
      kind,
      invokingUserId(ctx),
      limit,
      filter ? normalizeTag(filter, ctx.locale) : "all",
      expired ? "1" : "0",
    ].join(":");
    return legacyMessage(
      {
        allowed_mentions: { parse: [] },
        embeds: [
          {
            title: `${kind === "ban" ? "Bans" : "Strikes"} · ${shown}/${result.count}`,
            description: description || "No matching records.",
            color: await serverEmbedColor(ctx),
          },
        ],
        components: [
          actionRow({
            type: 2,
            style: 2,
            label: "Refresh",
            ...(emoji.component("refresh")
              ? { emoji: emoji.component("refresh") }
              : {}),
            custom_id: id,
          }),
        ],
      },
      { ephemeral: true },
    );
  }
  if (action === "remove") {
    const raw = stringOption(ctx, kind === "ban" ? "player" : "strike_id");
    if (!raw) throw new CommandInputError("Choose a record to remove.");
    const id = kind === "ban" ? normalizeTag(raw, ctx.locale) : raw;
    if (kind === "strike" && !/^[A-Za-z0-9_-]{1,20}$/u.test(id))
      throw new CommandInputError("Choose a valid strike ID.");
    await ctx.services.api.delete(`${base}/${encodeURIComponent(id)}`);
    return legacyMessage(
      {
        content: `Removed ${kind} record for ${id}.`,
        allowed_mentions: { parse: [] },
      },
      { ephemeral: true },
    );
  }
  if (action !== "add")
    throw new CommandInputError("Choose add, remove or list.");
  const tag = normalizeTag(stringOption(ctx, "player") ?? "", ctx.locale),
    reason = stringOption(ctx, "reason");
  if (!reason || reason.length > 1000)
    throw new CommandInputError("Enter a reason of up to 1,000 characters.");
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
  const result = await ctx.services.api.post<{
    strike_id?: string;
    player_name?: string;
  }>(`${base}/${encodeURIComponent(tag)}`, body);
  return legacyMessage(
    {
      allowed_mentions: { parse: [] },
      embeds: [
        {
          title: kind === "ban" ? "Ban record saved" : "Strike added",
          description: `**${escapeMarkdown(result.player_name ?? tag)}** · ${tag}\n${escapeMarkdown(reason)}${result.strike_id ? `\nID: \`${result.strike_id}\`` : ""}`,
          color: await serverEmbedColor(ctx),
          ...(image ? { image: { url: image } } : {}),
        },
      ],
    },
    { ephemeral: true },
  );
}
export function dispatchModeration(
  ctx: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> | DiscordInteractionResponse {
  authorize(ctx);
  const parts = (ctx.interaction.data?.custom_id ?? "").split(":");
  if (
    parts.length !== 7 ||
    parts[0] !== "ck" ||
    parts[1] !== "moderation" ||
    !["ban", "strike"].includes(parts[2]!) ||
    parts[3] !== invokingUserId(ctx) ||
    !["0", "1"].includes(parts[6]!)
  )
    throw new CommandInputError(
      "This private moderation control belongs to another user.",
    );
  const options = new Map(ctx.options);
  options.set("limit", {
    name: "limit",
    type: OptionType.Integer,
    value: Number(parts[4]),
  });
  options.set("expired", {
    name: "expired",
    type: OptionType.Boolean,
    value: parts[6] === "1",
  });
  if (parts[5] !== "all")
    options.set("player", {
      name: "player",
      type: OptionType.String,
      value: parts[5],
    });
  const run = executeModeration(
    { ...ctx, path: ["list"], options },
    parts[2] as Kind,
  );
  if (!waitUntil) return run;
  waitUntil(
    run
      .then((reply) =>
        ctx.services.discordRest.editOriginalInteractionResponse(
          ctx.interaction.token,
          reply.data ?? {},
        ),
      )
      .catch(() =>
        ctx.services.discordRest.editOriginalInteractionResponse(
          ctx.interaction.token,
          { content: "Unable to refresh moderation records." },
        ),
      ),
  );
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
