import random
import string
from collections import defaultdict
from datetime import timedelta

import coc
import disnake
import pendulum as pend

from classes.bot import CustomClient
from classes.database.models.player.strikes import StrikedPlayer
from exceptions.CustomExceptions import MessageException, NoLinkedAccounts
from utility.general import get_guild_icon, safe_run


async def add_strike(
    bot: CustomClient,
    player: coc.Player,
    added_by: disnake.User | disnake.Member,
    guild: disnake.Guild,
    reason: str,
    rollover_days: int = None,
    strike_weight: int = 1,
    dm_player: str = None,
):
    now = pend.now(tz=pend.UTC)
    dt_string = now.strftime('%Y-%m-%d %H:%M:%S')

    source = string.ascii_letters
    strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()

    is_used = await bot.strikelist.find_one({'strike_id': strike_id})
    while is_used is not None:
        strike_id = str(''.join((random.choice(source) for i in range(5)))).upper()
        is_used = await bot.strikelist.find_one({'strike_id': strike_id})

    if rollover_days is not None:
        now = pend.now(tz=pend.UTC)
        rollover_days = now + timedelta(rollover_days)
        rollover_days = int(rollover_days.timestamp())

    await bot.strikelist.insert_one(
        {
            'tag': player.tag,
            'date_created': dt_string,
            'reason': reason,
            'server': guild.id,
            'added_by': added_by.id,
            'strike_weight': strike_weight,
            'rollover_date': rollover_days,
            'strike_id': strike_id,
        }
    )

    gte = int(pend.now(tz=pend.UTC).timestamp())
    results = await bot.strikelist.find(
        {
            '$and': [
                {'tag': player.tag},
                {'server': guild.id},
                {
                    '$or': [
                        {'rollover_date': None},
                        {'rollover_date': {'$gte': gte}},
                    ]
                },
            ]
        }
    ).to_list(length=None)
    num_strikes = sum([result.get('strike_weight') for result in results])

    if rollover_days is not None:
        rollover_days = f'<t:{rollover_days}:f>'
    else:
        rollover_days = 'Never'
    embed = disnake.Embed(
        description=f"**Strike added to [{player.name}]({player.share_link}) [{player.clan.name if player.clan else 'No Clan'}] by {added_by.mention}.**\n"
        f'Strike Weight: {strike_weight}, Total Strikes Now: {num_strikes}\n'
        f'Rollover: {rollover_days}\n'
        f'Reason: {reason}',
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
                    embed.set_footer(text=f'Strike ID: {strike_id} | Notified in DM')
                except:
                    embed.set_footer(text=f'Strike ID: {strike_id} | DM Notification Failed')
    else:
        embed.set_footer(text=f'Strike ID: {strike_id}')
    await send_strike_log(bot=bot, guild=guild, reason=embed)

    return embed


async def send_strike_log(bot: CustomClient, guild: disnake.Guild, reason: disnake.Embed):
    server_db = await bot.ck_client.get_server_settings(server_id=guild.id)
    if server_db.strike_log_channel is not None:
        strike_log_channel = await bot.getch_channel(channel_id=server_db.strike_log_channel)
        if strike_log_channel is not None:
            await safe_run(func=strike_log_channel.send, embed=reason)


async def create_embeds(
    bot: CustomClient,
    guild: disnake.Guild,
    view: str,
    strike_clan: coc.Clan | None,
    strike_user: disnake.User | disnake.Member | None,
    strike_amount: int,
    view_non_family: bool,
    view_expired_strikes: bool,
    embed_color: disnake.Color,
):

    gte = int(pend.now(tz=pend.UTC).timestamp())
    if view_expired_strikes:
        gte = 0
    if strike_user:
        linked_accounts = await bot.link_client.get_linked_players(discord_id=strike_user.id)
        if not linked_accounts:
            raise NoLinkedAccounts
        all_strikes = (
            await bot.strikelist.find(
                {
                    '$and': [
                        {'server': guild.id},
                        {'tag': {'$in': linked_accounts}},
                        {
                            '$or': [
                                {'rollover_date': None},
                                {'rollover_date': {'$gte': gte}},
                            ]
                        },
                    ]
                }
            )
            .sort('date_created', 1)
            .to_list(length=None)
        )
    elif strike_clan:
        all_strikes = (
            await bot.strikelist.find(
                {
                    '$and': [
                        {'server': guild.id},
                        {'tag': {'$in': [m.tag for m in strike_clan.members]}},
                        {
                            '$or': [
                                {'rollover_date': None},
                                {'rollover_date': {'$gte': gte}},
                            ]
                        },
                    ]
                }
            )
            .sort('date_created', 1)
            .to_list(length=None)
        )
    else:
        if view_non_family:
            all_strikes = (
                await bot.strikelist.find(
                    {
                        '$and': [
                            {'server': guild.id},
                            {
                                '$or': [
                                    {'rollover_date': None},
                                    {'rollover_date': {'$gte': gte}},
                                ]
                            },
                        ]
                    }
                )
                .sort('date_created', 1)
                .to_list(length=None)
            )
        else:
            clan_member_tags = await bot.get_family_member_tags(guild_id=guild.id)
            all_strikes = (
                await bot.strikelist.find(
                    {
                        '$and': [
                            {'server': guild.id},
                            {'tag': {'$in': clan_member_tags}},
                            {
                                '$or': [
                                    {'rollover_date': None},
                                    {'rollover_date': {'$gte': gte}},
                                ]
                            },
                        ]
                    }
                )
                .sort('date_created', 1)
                .to_list(length=None)
            )

    if not all_strikes:
        raise MessageException('No Strikes Found')

    text = []
    hold = ''
    num = 0

    striked_tags = list(set(strk.get('tag') for strk in all_strikes))
    players: list[coc.Player] = await bot.get_players(tags=striked_tags, custom=False)
    players_map = {p.tag: p for p in players}

    if view == 'Strike View':
        for strike in all_strikes:
            tag = strike.get('tag')
            player = players_map.get(tag)
            if player is None:
                continue

            striked_player = StrikedPlayer(data=player._raw_data, client=None, results=strike)
            name = disnake.utils.escape_markdown(striked_player.name)
            date = striked_player.date_created[:10]

            added_by = ''
            if striked_player.added_by is not None:
                user = await bot.getch_user(strike.get('added_by'))
                added_by = f'{user}'
            clan = (
                f'{striked_player.clan.name}, {str(striked_player.role)}'
                if striked_player.clan is not None
                else 'No Clan'
            )

            rollover_days = strike.get('rollover_date')
            if rollover_days is not None:
                rollover_days = f'<t:{rollover_days}:f>'
            else:
                rollover_days = 'Never'

            hold += (
                f'{bot.fetch_emoji(striked_player.town_hall)}[{name}]({striked_player.share_link}) | {striked_player.tag}\n'
                f"{clan} | ID: {strike.get('strike_id')}\n"
                f'Added on: {date}, by {added_by}\n'
                f'Rollover Date: {rollover_days}\n'
                f'*{striked_player.reason}*\n\n'
            )
            num += 1
            if num == 10:
                text.append(hold)
                hold = ''
                num = 0

    elif view == 'Player View':
        stacked_strikes = defaultdict(list)
        for strike in all_strikes:
            stacked_strikes[strike.get('tag')].append(strike)

        for tag, strike_list in stacked_strikes.items():
            total_strike_weight = sum([result.get('strike_weight') for result in strike_list])
            num_strikes = len(strike_list)
            if num_strikes < strike_amount:
                continue

            player = players_map.get(tag)
            if player is None:
                continue

            strike_reason_ids = '\n'.join(
                [
                    f"`{result.get('strike_id')}` | "
                    f"{bot.timestamp(unix_time=int(pend.from_format(result.get('date_created'), 'YYYY-MM-DD HH:mm:ss', tz=pend.UTC).timestamp())).slash_date}"
                    f"\n - {result.get('reason')}"
                    for result in strike_list
                ]
            )
            clan = f'{player.clan.name}, {str(player.role)}' if player.clan is not None else 'No Clan'

            hold += (
                f'{bot.fetch_emoji(player.town_hall)}[{disnake.utils.escape_markdown(player.name)}]({player.share_link}) | {clan}\n'
                f'\# of Strikes: {num_strikes}, Weight: {total_strike_weight}\n'
                f'{strike_reason_ids}\n\n'
            )
            num += 1
            if num == 10:
                text.append(hold)
                hold = ''
                num = 0

    if num != 0:
        text.append(hold)

    embeds = []
    for t in text:
        embed = disnake.Embed(description=t, color=embed_color)
        embed.set_author(name=f'{guild.name} Strike List', icon_url=get_guild_icon(guild=guild))
        embeds.append(embed)

    return embeds


def chosen_text(self, clans: list[coc.Clan], ths, roles):
    text = ''
    if clans:
        text += '**CLANS:**\n'
        for clan in clans:
            text += f'• {clan.name} ({clan.tag})\n'
    if ths:
        text += '**THS:**\n'
        for th in ths:
            text += f'• {self.bot.fetch_emoji(name=th)} TH{th}\n'
    if roles:
        text += '**ROLES:**\n'
        for role in roles:
            text += f'• {role}\n'
    return text


def gen_percent(self):
    return [f'{x}%' for x in range(1, 101)]


def gen_capital_gold(self):
    return [f'Under {x} Capital Gold' for x in range(5000, 105000, 5000)]


def gen_missed_hits_war(self):
    return ['Per Missed Hit']


def gen_missed_hits_capital(self):
    return ['1+ hit', '2+ hits', '3+ hits', '4+ hits', '5+ hits']


def gen_days(self):
    return [f'{x} days' for x in range(1, 31)]


def gen_points(self):
    return [f'Under {x} points' for x in range(500, 4500, 500)]


async def add_autostrike(
    self,
    guild: disnake.Guild,
    autostrike_type: str,
    basic_filter: float,
    weight: int,
    rollover_days: int,
):
    pass
