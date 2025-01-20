from datetime import timedelta

import coc
import disnake
import pendulum as pend

from classes.bot import CustomClient
from classes.exceptions import MessageException
from utility.general import safe_run
from utility.discord.commands import register_button
from api.other import ObjectDictIterable
from api.bans import BanListItem

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
    bot: CustomClient,
    player: coc.Player,
    removed_by: disnake.User,
    guild: disnake.Guild,
    locale: disnake.Locale,
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


@register_button("banlist", parser="_:server")
async def create_embeds(
    bot: CustomClient,
    guild: disnake.Guild,
    embed_color: disnake.Color,
    locale: disnake.Locale,
):
    _, locale = bot.get_localizator(locale=locale)

    bans = await bot.ck_client.get_ban_list(server_id=guild.id)

    if not bans:
        return disnake.Embed(
            description=_('no-banned-players'),
            color=disnake.Color.red(),
        )

    embeds = []

    hold = ''
    banned_players = await bot.coc_client.fetch_players(player_tags=bans.key_list())
    for count, banned_player in enumerate(banned_players, 1):
        ban = bans[banned_player.tag]
        if ban is None:
            continue

        clan = _('no-clan')
        if banned_player.clan is not None:
            clan = f'{banned_player.clan.name}, {banned_player.role}'

        added_by = ''
        if ban.added_by is not None:
            user = await guild.getch_member(ban.added_by)
            if not user:
                user = await bot.getch_user(ban.added_by)
            added_by = f'\n{_("ban-added-by")} {user}'
        hold += (
            f'{bot.fetch_emoji(banned_player.town_hall)}[{banned_player.name}]({banned_player.share_link}) | {banned_player.tag}\n'
            f'{clan}\n'
            f'{_("ban-added-on")} {ban._date_created}\n'
            f'{_("reason-notes")}: *{ban.notes}*{added_by}\n\n'
        )

        if count % 10 == 0 or count == len(banned_players):
            embed = disnake.Embed(description=hold, color=embed_color)
            embed.set_author(
                name=_('server-ban-list', values={'server_name': guild.name}),
                icon_url=bot.get_guild_icon(guild=guild),
            )
            embeds.append(embed)
            hold = ''

    return embeds
