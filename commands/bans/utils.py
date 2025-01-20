from datetime import timedelta

import coc
import disnake
import pendulum as pend

from classes.bot import CustomClient
from classes.exceptions import MessageException
from utility.general import safe_run
from utility.discord.commands import register_button


async def add_ban(
    bot: CustomClient,
    player: coc.Player,
    added_by: disnake.User | disnake.Member,
    guild: disnake.Guild,
    reason: str,
    rollover_days: int = None,
    dm_player: str = None,
    locale: disnake.Locale = disnake.Locale.en_US,
):
    _, locale = bot.get_localizator(locale=locale)

    now = pend.now(tz=pend.UTC)
    dt_string = now.strftime('%Y-%m-%d %H:%M:%S')

    if reason is None:
        reason = _('reason-default')

    if rollover_days is not None:
        now = pend.now(tz=pend.UTC)
        rollover_days = now + timedelta(rollover_days)
        rollover_days = int(rollover_days.timestamp())

    find_ban = await bot.banlist.find_one({'$and': [{'VillageTag': player.tag}, {'server': guild.id}]})
    if find_ban:
        await bot.banlist.update_one(
            {'$and': [{'VillageTag': player.tag}, {'server': guild.id}]},
            {
                '$set': {'Notes': reason, 'rollover_date': rollover_days},
                '$push': {
                    'edited_by': {
                        'user': added_by.id,
                        'previous': {
                            'reason': find_ban.get('Notes'),
                            'rollover_days': find_ban.get('rollover_date'),
                        },
                    }
                },
            },
        )
        ban_type = 'updated'
    else:
        await bot.banlist.insert_one(
            {
                'VillageTag': player.tag,
                'DateCreated': dt_string,
                'Notes': reason,
                'server': guild.id,
                'added_by': added_by.id,
                'rollover_date': rollover_days,
                'name': player.name,
            }
        )
        ban_type = 'added'

    clan_text = _('no-clan')
    if player.clan:
        clan_text = f'[{player.clan.name}]({player.clan.share_link})'

    embed = disnake.Embed(
        description=f'**{bot.fetch_emoji(player.town_hall)}[{player.name}]({player.share_link})** | {player.tag}'
        f'{clan_text}\n'
        f"{_('ban-details', values={'ban_type' : ban_type, 'date' : dt_string, 'discord_mention' : added_by.mention})}\n"
        f'{_("reason-notes")}: {reason}',
        color=disnake.Color.brand_red(),
    )

    embed.timestamp = now
    if dm_player is not None:
        linked_account = await bot.link_client.get_link(player_tag=player.tag)
        if linked_account:
            server_member = await guild.getch_member(linked_account)
            if server_member:
                try:
                    await server_member.send(content=dm_player, embed=embed)
                    embed.set_footer(text=_('Notified in DM'))
                except:
                    embed.set_footer(text=_('DM Notification Failed'))
    await send_ban_log(bot=bot, guild=guild, reason=embed)

    return embed


async def remove_ban(
    bot: CustomClient, player: coc.Player, removed_by: disnake.User, guild: disnake.Guild, locale: disnake.Locale
):
    _, locale = bot.get_localizator(locale=locale)

    results = await bot.banlist.find_one({'$and': [{'VillageTag': player.tag}, {'server': guild.id}]})
    if not results:
        raise MessageException(_('not-banned', values={'player_name': player.name}))

    await bot.banlist.find_one_and_delete({'$and': [{'VillageTag': player.tag}, {'server': guild.id}]})

    embed = disnake.Embed(
        description=_(
            'unbanned',
            values={
                'player_name': player.name,
                'player_link': player.share_link,
                'discord_mention': removed_by.mention,
            },
        ),
        color=disnake.Color.orange(),
    )

    await send_ban_log(bot=bot, guild=guild, reason=embed)
    return embed


async def send_ban_log(bot: CustomClient, guild: disnake.Guild, reason: disnake.Embed):
    server_db = await bot.ck_client.get_server_settings(server_id=guild.id)
    if server_db.banlist_channel is not None:
        ban_log_channel = await bot.getch_channel(channel_id=server_db.banlist_channel)
        if ban_log_channel is not None:
            await safe_run(func=ban_log_channel.send, embed=reason)


@
async def create_embeds(
    bot: CustomClient, bans: list, guild: disnake.Guild, embed_color: disnake.Color, locale: disnake.Locale
):
    _, locale = bot.get_localizator(locale=locale)

    embeds = []
    banned_tags = [b.get('VillageTag') for b in bans]
    discord_links = await bot.link_client.get_links(*banned_tags)
    discord_links = dict(discord_links)

    hold = ''
    banned_players: list[BannedPlayer] = await bot.get_players(
        tags=banned_tags, custom=BannedPlayer, use_cache=True, found_results=bans
    )
    for count, banned_player in enumerate(banned_players, 1):
        date = banned_player.date_created[0:10]
        notes = banned_player.notes

        clan = _('no-clan')
        if banned_player.clan is not None:
            clan = f'{banned_player.clan.name}, {banned_player.role}'

        discord = ''
        if discord_id := discord_links.get(banned_player.tag):
            if discord_id is not None:
                discord_user = guild.get_member(int(discord_id))
                if discord_user:
                    discord = f'{_("banned-discord")} {discord_user.mention} ({discord_user.name})\n'
        added_by = ''
        if banned_player.added_by is not None:
            user = await bot.getch_user(banned_player.added_by)
            added_by = f'\n{_("ban-added-by")} {user}'
        hold += (
            f'{bot.fetch_emoji(banned_player.town_hall)}[{banned_player.name}]({banned_player.share_link}) | {banned_player.tag}\n'
            f'{discord}'
            f'{clan}\n'
            f'{_("ban-added-on")} {date}\n'
            f'{_("reason-notes")}: *{notes}*{added_by}\n\n'
        )

        if count % 10 == 0 or count == len(banned_players):
            embed = disnake.Embed(description=hold, color=embed_color)
            embed.set_author(
                name=_('server-ban-list', values={'server_name': guild.name}), icon_url=get_guild_icon(guild=guild)
            )
            embeds.append(embed)
            hold = ''

    return embeds
