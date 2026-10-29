import { actionRow, legacyMessage } from "../discord/components";
import { InteractionResponseType, InteractionType, MessageFlags } from "../discord/types";
import { CommandInputError, OptionType, stringOption } from "./command-utils";
import { serverEmbedColor } from "./embed-color";
import { emojis } from "./game-common";
import type { ApplicationCommandDefinition, ApplicationCommandOption, Command, CommandContext } from "./types";

const categories = {
  all: { label: "All commands", roots: [] as string[] },
  players: { label: "Players & rankings", roots: ["player", "ranked", "legends", "leaderboard", "stats"] },
  clans: { label: "Clans & wars", roots: ["clan", "family", "war", "cwl", "graph", "boosts"] },
  accounts: { label: "Your accounts", roots: ["link", "refresh", "main-account", "privacy"] },
  tools: { label: "Tools & sharing", roots: ["army", "base", "fankit", "pepe", "help", "dashboard", "role-users", "reminders"] },
  server: { label: "Rosters & moderation", roots: ["roster", "ban", "strike", "ticket"] },
};
type Category = keyof typeof categories;
function leaves(definitions: ApplicationCommandDefinition[]) {
  const rows: Array<{ path: string; description: string; options: ApplicationCommandOption[] }> = [];
  for (const root of definitions) {
    const visit = (path: string, description: string, options: ApplicationCommandOption[]) => {
      const children = options.filter(option => option.type === OptionType.Subcommand || option.type === OptionType.SubcommandGroup);
      if (children.length) for (const child of children) visit(`${path} ${child.name}`, child.description, child.options ?? []);
      else rows.push({ path, description, options });
    };
    visit(root.name, root.description, root.options ?? []);
  }
  return rows;
}
export const helpCommand: Command = {
  deferred: true,
  definition: {
    name: "help", description: "Browse ClashKing commands", type: 1,
    integration_types: [0, 1], contexts: [0, 1, 2],
    options: [
      { name: "command", description: "Command to explain", type: OptionType.String, autocomplete: true },
      { name: "category", description: "Browse a command category", type: OptionType.String,
        choices: Object.entries(categories).map(([value, item]) => ({ name: item.label, value })) },
    ],
  },
  async autocomplete(ctx) {
    const { commandDefinitions } = await import("./registry");
    const query = (stringOption(ctx, "command") ?? "").toLowerCase().replace(/^\//u, "").trim();
    return leaves(commandDefinitions).filter(row => row.path.includes(query)).slice(0, 25)
      .map(row => ({ name: `/${row.path}`.slice(0, 100), value: row.path }));
  },
  async execute(ctx) {
    // Build visible help from registration, so removed setup paths cannot survive
    // in a second hand-maintained command catalogue. Categories group roots only.
    const { commandDefinitions } = await import("./registry");
    const selected = (stringOption(ctx, "command") ?? "").replace(/^\//u, "").trim().replace(/\s+/gu, " ");
    const category = stringOption(ctx, "category") ?? "all";
    if (!Object.hasOwn(categories, category)) throw new CommandInputError("Choose a command category.");
    const currentCategory = category as Category;
    const root = commandDefinitions.find(row => row.name === selected);
    const leaf = leaves(commandDefinitions).find(row => row.path === selected);
    if (selected && !root && !leaf) throw new CommandInputError("Choose a current command from autocomplete.");
    let title = currentCategory === "all" ? "ClashKing commands" : categories[currentCategory].label;
    let description = "";
    if (leaf) {
      title = `/${leaf.path}`;
      description = leaf.description;
      for (const option of leaf.options) {
        const range = [option.min_value !== undefined ? `min ${option.min_value}` : "", option.max_value !== undefined ? `max ${option.max_value}` : ""].filter(Boolean).join(", ");
        const line = `**${option.name}** · ${option.required ? "Required" : "Optional"}\n${option.description}${range ? ` (${range})` : ""}${option.choices?.length ? `\n${option.choices.map(choice => choice.name).join(" · ")}` : ""}`;
        if (description.length + line.length + 2 > 3400) break;
        description += `\n\n${line}`;
      }
    } else if (root) {
      title = `/${root.name}`;
      description = leaves([root]).map(row => `**/${row.path}**\n${row.description}`).join("\n\n");
    } else {
      const roots = categories[currentCategory].roots;
      description = commandDefinitions.filter(row => !roots.length || roots.includes(row.name))
        .map(row => `**/${row.name}** · ${row.description}`).join("\n");
    }
    const refresh = (await emojis(ctx)).component("refresh") ?? { name: "↻" };
    return legacyMessage({
      allowed_mentions: { parse: [] },
      embeds: [{ title, color: await serverEmbedColor(ctx), description: description.slice(0, 3900) }],
      components: [
        actionRow({ type: 3, custom_id: "ck:help:category", placeholder: "Browse commands",
          options: Object.entries(categories).map(([value, item]) => ({ label: item.label, value, default: !selected && value === category })) }),
        actionRow({ type: 2, style: 2, emoji: refresh,
          custom_id: `ck:help:refresh:${category}:${selected ? selected.replaceAll(" ", "~") : "-"}` }),
      ],
    });
  },
};
export async function dispatchHelpControl(ctx: CommandContext, waitUntil?: (promise: Promise<unknown>) => void) {
  if (ctx.interaction.type !== InteractionType.MessageComponent) throw new CommandInputError("This help control is no longer available.");
  const id = ctx.interaction.data?.custom_id ?? "", parts = id.split(":");
  let category: string, command = "";
  if (id === "ck:help:category" && ctx.interaction.data?.component_type === 3 && ctx.interaction.data.values?.length === 1) category = ctx.interaction.data.values[0] ?? "";
  else if (parts.length === 5 && parts[2] === "refresh" && ctx.interaction.data?.component_type === 2) {
    category = parts[3]!;
    command = parts[4] === "-" ? "" : parts[4]!.replaceAll("~", " ");
  } else throw new CommandInputError("This help control is no longer available.");
  if (!Object.hasOwn(categories, category)) throw new CommandInputError("Choose a command category.");
  const options = new Map<string, { name: string; type: number; value: string }>([["category", { name: "category", type: OptionType.String, value: category }]]);
  if (command) options.set("command", { name: "command", type: OptionType.String, value: command });
  const run = () => helpCommand.execute({ ...ctx, options });
  if (!waitUntil) return { ...(await run()), type: InteractionResponseType.UpdateMessage };
  waitUntil(run().then(response => ctx.services.discordRest.editOriginalInteractionResponse(ctx.interaction.token, response.data ?? {}))
    .catch(() => ctx.services.discordRest.createInteractionFollowup(ctx.interaction.token, { content: "Couldn't refresh help. Please try again.", flags: MessageFlags.Ephemeral })));
  return { type: InteractionResponseType.DeferredUpdateMessage };
}
