import { ClashKingApiError } from '../api/client';
import { legacyMessage } from '../discord/components';
import { CommandInputError, invokingUserId, OptionType, requireGuildId, stringOption } from './command-utils';
import { fetchPlayer, lookupPlayerAutocomplete, playerLabel, playerOption, resolvePlayerTag, subcommand, userOption } from './game-common';
import { serverEmbedColor } from './embed-color';
import type { Command } from './types';

const denials = new Set([
  'You need Dashboard Links manage permission',
  'This player must belong to a family clan linked to this server',
  'Verify this family clan before managing its unverified links',
  'This player is not in the selected family clan',
  'Choose a current Discord server member',
  'Verified account links can only be changed by their owner',
  'This account is already linked. Remove its unverified link before assigning it again',
  'This account has no link to remove',
]);

export const modlinkCommand: Command = {
  deferred: true,
  ephemeral: true,
  // Do not gate this on Discord's Manage Server bit. A delegated Dashboard
  // Links manager is eligible too; the API checks that actor on every write.
  definition: { name: 'modlink', description: 'Manage unverified links in verified family clans', type: 1, contexts: [0], integration_types: [0], options: [
    { name: 'add', description: 'Link a family player to a Discord member', type: OptionType.Subcommand, options: [playerOption, { ...userOption, required: true }] },
    { name: 'remove', description: 'Remove an unverified family player link', type: OptionType.Subcommand, options: [playerOption] },
  ] },
  autocomplete: lookupPlayerAutocomplete,
  async execute(context) {
    const ctx = subcommand(context), serverId = requireGuildId(ctx), action = ctx.path[0];
    if (action !== 'add' && action !== 'remove') throw new CommandInputError('Choose add or remove.');
    const playerTag = await resolvePlayerTag(ctx), player = await fetchPlayer(ctx, playerTag);
    if (!player.clan?.tag) throw new CommandInputError('This player must belong to a family clan linked to this server.');
    const userId = stringOption(ctx, 'discord_user');
    if (action === 'add' && !userId) throw new CommandInputError('Choose a Discord server member.');
    try {
      await ctx.services.api.post(`/v2/bot/servers/${serverId}/modlinks`, {
        action, actorId: invokingUserId(ctx), clanTag: player.clan.tag, playerTag,
        ...(action === 'add' ? { userId } : {}),
      });
    } catch (cause) {
      if (cause instanceof ClashKingApiError) {
        let message = '';
        try { message = JSON.parse(cause.body)?.message ?? ''; } catch { /* Keep unexpected upstream failures in the standard error path. */ }
        if (denials.has(message)) throw new CommandInputError(`${message}.`);
      }
      throw cause;
    }
    return legacyMessage({ allowed_mentions: { parse: [] }, embeds: [{ color: await serverEmbedColor(ctx), description:
      action === 'add' ? `Linked ${playerLabel(player)} to <@${userId}>.\nThis link is unverified.` : `Removed the unverified link for ${playerLabel(player)}.` }] }, { ephemeral: true });
  },
};
