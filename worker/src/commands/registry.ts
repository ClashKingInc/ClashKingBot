import { interactionErrorReply, sendInteractionError } from "./errors";
import { dispatchCwlSearch } from "./cwl-search";
import { dispatchLegendStats } from "./legend-global";
import { dispatchClanControl } from "./clan-controls";
import { dispatchClanLinks } from "./link-list";
import { dispatchGraphControl } from "./graph-controls";
import { fankitCommand, dispatchFankit } from "./fankit";
import { memeCommand, dispatchMeme } from "./meme";
import { quickMemberAction } from "./buttons";
import { botInfoCommand } from "./bot-info";
import { graphCommand } from "./graph";
import { roleUsersCommand } from "./role-users";
import { dispatchHelpControl, helpCommand } from "./help";
import { dispatchMemberReport } from "./member-reports";
import {
  InteractionResponseType,
  InteractionType,
  MessageFlags,
  type DiscordInteraction,
  type DiscordInteractionResponse,
  type InteractionOption,
} from "../discord/types";
import type { Env } from "../env";
import { resolveLocale, translate } from "../localization/catalog";
import { baseCommand, baseComponentHandlers } from "./base";
import { CommandInputError, invokingUserId } from "./command-utils";
import { linkCommand, linkComponentHandlers, unlinkCommand } from "./link";
import { dispatchRoster, rosterCommand } from "./roster";
import { refreshCommand, dispatchRefresh } from "./refresh";
import { remindersCommand } from "./reminders";
import { dashboardCommand } from "./dashboard";
import { ticketCommand } from "./ticket";
import { dispatchWarPanel } from "./war-panel";
import { playerCommand } from "./player";
import { rankedCommand } from "./ranked";
import { legendsCommand } from "./legends";
import { leaderboardCommand } from "./leaderboard";
import { armyCommand } from "./army";
import { moderationCommand, dispatchModeration } from "./moderation";
import { warCommand, cwlCommand, dispatchWar } from "./war";
import { familyCommand } from "./family";
import { clanCommand } from "./clan";
import { dispatchGamePage } from "./game-pages";
import type { Command, CommandContext, CommandServices, ComponentHandler } from "./types";

// Setup and automation live in the dashboard. Keep only member-facing and
// informational slash commands here; persistent message handlers remain below.
const commands: readonly Command[] = [fankitCommand,memeCommand,botInfoCommand,graphCommand,roleUsersCommand,helpCommand,baseCommand, linkCommand, rosterCommand, refreshCommand, remindersCommand, dashboardCommand, ticketCommand, playerCommand, rankedCommand, legendsCommand, leaderboardCommand, armyCommand, clanCommand, familyCommand, moderationCommand, warCommand, cwlCommand];
const commandByName = new Map(commands.map((command) => [command.definition.name, command]));
// Retain cached legacy invocations without registering a separate slash root.
commandByName.set("unlink", unlinkCommand);
const componentHandlers = new Map<string, ComponentHandler>([
  ...baseComponentHandlers,
  ...linkComponentHandlers,
]);

export const commandDefinitions = commands.map((command) => command.definition);

export async function dispatchInteraction(
  interaction: DiscordInteraction,
  env: Env,
  services: CommandServices,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const context = createContext(interaction, env, services);
  if (interaction.type === InteractionType.ApplicationCommandAutocomplete) {
    const command = commandByName.get(interaction.data?.name ?? "");
    try {
      return { type: InteractionResponseType.ApplicationCommandAutocompleteResult,
        data: { choices: command?.autocomplete ? await command.autocomplete(context) : [] } };
    } catch {
      return { type: InteractionResponseType.ApplicationCommandAutocompleteResult, data: { choices: [] } };
    }
  }
  try {
  if (interaction.type === InteractionType.ApplicationCommand) {
    return await executeCommand(context, waitUntil);
  }
  if (interaction.type === InteractionType.MessageComponent || interaction.type === InteractionType.ModalSubmit) {
    return await executePersistentHandler(context, waitUntil);
  }
  return unknownInteraction(context.locale,interaction);
  } catch(error) { return interactionErrorReply(error,interaction); }
}

function createContext(interaction: DiscordInteraction, env: Env, services: CommandServices): CommandContext {
  return {
    env,
    interaction,
    locale: resolveLocale(interaction.locale, interaction.guild_locale),
    options: flattenOptions(interaction.data?.options ?? []),
    path: [],
    services,
  };
}

async function executeCommand(
  context: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const name = context.interaction.data?.name;
  const command = name ? commandByName.get(name) : undefined;
  if (!command) {
    // Cached setup definitions can outlive registration; guide users without
    // retaining a hidden write path through an old Discord command.
    if (name && ["autorefresh", "roles", "giveaway", "buttons"].includes(name)) {
      return { type: InteractionResponseType.ChannelMessageWithSource,
        data: { content: "Server setup is managed in /setup.", flags: MessageFlags.Ephemeral } };
    }
    return unknownInteraction(context.locale);
  }
  const ephemeral = typeof command.ephemeral === "function" ? await command.ephemeral(context) : command.ephemeral;
  const deferred = typeof command.deferred === "function" ? command.deferred(context) : command.deferred;
  if (!deferred || !waitUntil) {
    return command.execute(context);
  }
  waitUntil(command.execute(context).then(
    async (response) => {
      // Discord fixes visibility at acknowledgement time. A private result
      // after a public defer needs its own follow-up, not an ignored flag edit.
      if(!ephemeral&&typeof response.data?.flags==="number"&&(response.data.flags&MessageFlags.Ephemeral)){
        await context.services.discordRest.editOriginalInteractionResponse(context.interaction.token,{content:"This result is private.",embeds:[],components:[]});
        await context.services.discordRest.createInteractionFollowup(context.interaction.token,response.data??{});
        await context.services.discordRest.deleteOriginalInteractionResponse(context.interaction.token);
      }else await context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, response.data ?? {});
    },
  ).catch((error: unknown) => {
    // The first follow-up after a defer can resolve the original response.
    // Update it in place: deleting it would also delete the visible error.
    return sendInteractionError(context,error,true);
  }));
  return {
    data: ephemeral ? { flags: MessageFlags.Ephemeral } : {},
    type: InteractionResponseType.DeferredChannelMessageWithSource,
  };
}

async function executePersistentHandler(
  context: CommandContext,
  waitUntil?: (promise: Promise<unknown>) => void,
): Promise<DiscordInteractionResponse> {
  const customId = context.interaction.data?.custom_id ?? "";
  // Preserve legacy Reddit buttons and use the actual clicker's context.
  const redditPlayer = /^redditplayer_(#[0289PYLQGRJCUV]{1,15})$/u.exec(customId);
  if (redditPlayer) {
    const handler: ComponentHandler = async ctx => {
      const result = await playerCommand.execute({ ...ctx, options: new Map([["lookup", {
        name: "lookup", type: 1, options: [{ name: "player", type: 3, value: redditPlayer[1]! }],
      }]]) });
      return { ...result, data: { ...result.data, flags: Number(result.data?.flags ?? 0) | MessageFlags.Ephemeral } };
    };
    return waitUntil ? deferPersistentHandler(context, handler, [], waitUntil) : handler(context, []);
  }
  if(customId.startsWith("ck:cwl:"))return dispatchCwlSearch(context,waitUntil);
  if(customId.startsWith("ck:legendstats:"))return dispatchLegendStats(context,waitUntil);
  if(customId.startsWith("ck:clans:"))return dispatchClanControl(context,waitUntil);
  if(customId.startsWith("ck:help:"))return dispatchHelpControl(context,waitUntil);
  if(customId.startsWith("ck:chart:"))return dispatchGraphControl(context,waitUntil);
  if(customId.startsWith("ck:links:"))return dispatchClanLinks(context,waitUntil);
  if(customId.startsWith("ck:meme:"))return dispatchMeme(context,waitUntil);
  if(customId.startsWith("ck:fk:"))return dispatchFankit(context,waitUntil);
  // Old Legend History buttons still exist on Discord messages. Route them
  // through the same renderer as /legends history instead of maintaining a
  // second presentation or invalidating otherwise usable historical messages.
  if (/^legendhistory:#[0289PYLQGRJCUV]+$/u.test(customId)) {
    const tag = customId.slice("legendhistory:".length);
    return dispatchGamePage({ ...context, interaction: { ...context.interaction,
      data: { ...context.interaction.data, custom_id: `ck:page:lh:${invokingUserId(context)}:${tag}:0` },
    } }, waitUntil);
  }
  const legacyQuick:Record<string,string>={"Start Link":"link","Link Help":"help","Refresh Roles":"refresh",MyToDoList:"todo",MyRosters:"rosters"};
  if(legacyQuick[customId]&&context.interaction.guild_id)return executePersistentHandler({...context,interaction:{...context.interaction,data:{...context.interaction.data,custom_id:`ck:quick:${context.interaction.guild_id}:${legacyQuick[customId]}`}}},waitUntil);
  if(customId.startsWith("ck:quick:")){
    const match=/^ck:quick:([0-9]{15,20}):(link|help|refresh|todo|rosters)$/u.exec(customId);
    if(!match||match[1]!==context.interaction.guild_id)throw new CommandInputError("This panel belongs to another server.");
    if(match[2]==="link"||match[2]==="help"){
      const action=match[2]==="link"?"start":"help";
      return componentHandlers.get(`link:${action}`)!(context,[]);
    }
    const handler:ComponentHandler=async ctx=>{const response=await quickMemberAction(ctx,match[2]!);return {...response,data:{...response.data,flags:Number(response.data?.flags??0)|MessageFlags.Ephemeral}};};
    return waitUntil?deferPersistentHandler(context,handler,[],waitUntil):handler(context,[]);
  }
  if(customId.startsWith("ck:members:"))return dispatchMemberReport(context,waitUntil);
  // Automated panels use colon-separated IDs; command reports use pipes.
  // Route the panel format first so the report parser cannot swallow it.
  if(/^ck:war:(?:refresh|attacks|defenses|opponent):/u.test(customId))return dispatchWarPanel(context,waitUntil);
  if(customId.startsWith("ck:war:"))return dispatchWar(context,waitUntil);
  if(customId.startsWith("ck:moderation:"))return dispatchModeration(context,waitUntil);
  if(customId.startsWith("ck:page:"))return dispatchGamePage(context,waitUntil);
  if (customId.startsWith("ck:refresh:")) return dispatchRefresh(context, waitUntil);
  if (customId.startsWith("ck:roster:")) return dispatchRoster(context, waitUntil);
  if (customId === "link" || customId === "who") {
    const handler = componentHandlers.get("base:legacy");
    if (!handler) return unknownInteraction(context.locale);
    return waitUntil ? deferPersistentHandler(context, handler, [customId], waitUntil) : handler(context, [customId]);
  }
  const segments = customId.split(":");
  const prefix = segments.shift();
  const domain = prefix === "ck" ? segments.shift() : prefix;
  const action = segments.shift();
  if (!domain || !action || (prefix === "ck" ? domain !== "link" : domain !== "base")) return unknownInteraction(context.locale);
  if (domain === "base" && segments.length !== (action === "submit" ? 0 : 1)) return unknownInteraction(context.locale);
  if (domain === "link" && segments.length !== 0) return unknownInteraction(context.locale);
  const isSubmit = action === "submit";
  if (isSubmit !== (context.interaction.type === InteractionType.ModalSubmit)) return unknownInteraction(context.locale);
  const handler = domain && action ? componentHandlers.get(`${domain}:${action}`) : undefined;
  if (!handler) return unknownInteraction(context.locale);
  return (domain === "base" || isSubmit) && waitUntil
    ? deferPersistentHandler(context, handler, segments, waitUntil)
    : handler(context, segments);
}

function deferPersistentHandler(
  context: CommandContext,
  handler: ComponentHandler,
  segments: string[],
  waitUntil: (promise: Promise<unknown>) => void,
): DiscordInteractionResponse {
  waitUntil(completeDeferredInteraction(context, handler(context, segments)));
  return { data: { flags: MessageFlags.Ephemeral }, type: InteractionResponseType.DeferredChannelMessageWithSource };
}

async function completeDeferredInteraction(context: CommandContext, pending: Promise<DiscordInteractionResponse>): Promise<void> {
  try {
    const response = await pending;
    await context.services.discordRest.editOriginalInteractionResponse(context.interaction.token, response.data ?? {});
  } catch (error) {
    await sendInteractionError(context,error,true);
  }
}

function unknownInteraction(locale: string, interaction?:DiscordInteraction): DiscordInteractionResponse {
  return interactionErrorReply(new CommandInputError(translate("error.unknownCommand", locale)),interaction??{id:'unknown'} as DiscordInteraction);
}

function flattenOptions(options: InteractionOption[]): ReadonlyMap<string, InteractionOption> {
  return new Map(options.map((option) => [option.name, option]));
}
