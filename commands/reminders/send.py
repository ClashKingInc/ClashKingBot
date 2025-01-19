import datetime

import coc
import disnake
import pendulum as pend
from pytz import utc

from classes.bot import CustomClient
from classes.reminders import Reminder


async def war_reminder(
    bot: CustomClient,
    event: dict,
    manual_send: bool = False,
    channel: disnake.TextChannel = None,
):
    reminder_time = event.get('time')
    clan_tag = event.get('clan_tag')
    war: coc.ClanWar = coc.ClanWar(data=event.get('data'), client=None, clan_tag=clan_tag)
    missing = {}
    names = {}
    ths = {}
    for player in war.clan.members:
        if len(player.attacks) < war.attacks_per_member:
            missing[player.tag] = war.attacks_per_member - len(player.attacks)
            names[player.tag] = player.name
            ths[player.tag] = player.town_hall

    tags = list(missing.keys())
    if not missing:
        return
    links = await bot.link_client.get_links(*tags)
    links = dict(links)
    players = await bot.get_players(tags=tags, custom=False)
    players.sort(key=lambda x: x.town_hall, reverse=True)

    if not manual_send:
        all_reminders = bot.reminders.find(
            {
                '$and': [
                    {'clan': clan_tag},
                    {'type': 'War'},
                    {'time': f'{reminder_time}'},
                ]
            }
        )
        for reminder in await all_reminders.to_list(length=None):
            reminder = Reminder(bot=bot, data=reminder)
            if reminder.server_id not in bot.OUR_GUILDS:
                continue

            war_type = war.type.capitalize() if war.type != 'cwl' else war.type.upper()
            if war_type not in reminder.war_types:
                continue
            try:
                channel = await bot.getch_channel(reminder.channel_id)

            except (disnake.NotFound, disnake.Forbidden):
                await reminder.delete()
                continue

            server = await bot.getch_guild(reminder.server_id)
            if server is None:
                continue

            missing_text_list = []
            missing_text = ''
            start_text = (
                f'{bot.emoji.pin}**12 Hours Remaining in War**\n'
                f'{bot.emoji.pin}**{war.clan.name} vs {war.opponent.name}**\n'
                f'{bot.emoji.wood_swords}{war.clan.attacks_used}/{war.opponent.attacks_used} {bot.emoji.war_star}{war.clan.stars}/{war.opponent.stars}'
            )
            for war_member in players:
                if (
                    war_member.clan is not None
                    and war_member.clan.tag == war.clan_tag
                    and str(war_member.role) not in reminder.roles
                ):
                    continue
                if war_member.town_hall not in reminder.townhalls:
                    continue
                num_missing = missing[war_member.tag]
                name = names[war_member.tag]
                discord_id = links[war_member.tag]
                text_to_check = start_text
                if len(missing_text) + len(text_to_check) + 125 >= 2000:
                    missing_text_list.append(missing_text)
                    missing_text = ''
                if discord_id is None:
                    missing_text += f'({num_missing}/{war.attacks_per_member}) {bot.fetch_emoji(ths[war_member.tag])}{name} | {war_member.tag}\n'
                else:
                    missing_text += f'({num_missing}/{war.attacks_per_member}) {bot.fetch_emoji(ths[war_member.tag])}{name} | <@{discord_id}>\n'

            if missing_text != '':
                missing_text_list.append(missing_text)

            for text in missing_text_list:
                first_text = text == missing_text_list[0]
                last_text = text == missing_text_list[-1]
                if first_text:
                    text = (
                        f'{bot.emoji.clock}**{reminder_time} Remaining in War**\n'
                        f'{bot.emoji.pin}**{war.clan.name} vs {war.opponent.name}**\n'
                        f'{bot.emoji.wood_swords}{war.clan.attacks_used}/{war.opponent.attacks_used} {bot.emoji.war_star}{war.clan.stars}/{war.opponent.stars} '
                        f'{bot.emoji.time} {bot.timestamp(unix_time=int(war.end_time.time.replace(tzinfo=pend.UTC).timestamp())).relative}\n'
                        f'{text}'
                    )
                if last_text and reminder.custom_text:
                    text += f'\n{reminder.custom_text}'

                try:
                    await channel.send(content=text)
                except Exception:
                    pass
    else:
        missing_text_list = []
        missing_text = ''
        start_text = (
            f'{bot.emoji.pin}**12 Hours Remaining in War**\n'
            f'{bot.emoji.pin}**{war.clan.name} vs {war.opponent.name}**\n'
            f'{bot.emoji.wood_swords}{war.clan.attacks_used}/{war.opponent.attacks_used} {bot.emoji.war_star}{war.clan.stars}/{war.opponent.stars}'
        )
        for war_member in players:
            num_missing = missing[war_member.tag]
            name = names[war_member.tag]
            discord_id = links[war_member.tag]
            text_to_check = start_text
            if len(missing_text) + len(text_to_check) + 125 >= 2000:
                missing_text_list.append(missing_text)
                missing_text = ''
            if discord_id is None:
                missing_text += f'({num_missing}/{war.attacks_per_member}) {bot.fetch_emoji(ths[war_member.tag])}{name} | {war_member.tag}\n'
            else:
                missing_text += f'({num_missing}/{war.attacks_per_member}) {bot.fetch_emoji(ths[war_member.tag])}{name} | <@{discord_id}>\n'

        if missing_text != '':
            missing_text_list.append(missing_text)

        for text in missing_text_list:
            first_text = text == missing_text_list[0]
            last_text = text == missing_text_list[-1]
            if first_text:
                text = (
                    f'{bot.emoji.clock}**{reminder_time} Remaining in War**\n'
                    f'{bot.emoji.pin}**{war.clan.name} vs {war.opponent.name}**\n'
                    f'{bot.emoji.wood_swords}{war.clan.attacks_used}/{war.opponent.attacks_used} {bot.emoji.war_star}{war.clan.stars}/{war.opponent.stars} '
                    f'{bot.emoji.time} {bot.timestamp(unix_time=int(war.end_time.time.replace(tzinfo=pend.UTC).timestamp())).relative}\n'
                    f'{text}'
                )

            try:
                await channel.send(content=text)
            except Exception:
                pass


async def clan_capital_reminder(
    bot: CustomClient,
    server: disnake.Guild,
    raid_log_entry: coc.RaidLogEntry,
    clan: coc.Clan,
    reminder_time: str,
    custom_text: str,
    attack_threshold: int = 5,
    manual_send: bool = False,
    channel: disnake.TextChannel = None,
):

    missing = {}
    clan_members = {member.tag: member for member in clan.members}
    for member in raid_log_entry.members:  # type: coc.RaidMember
        x = clan_members.pop(member.tag, None)
        if member.attack_count == (member.attack_limit + member.bonus_attack_limit):
            continue
        if int(member.attack_count) < int(attack_threshold):
            missing[member.tag] = member

    missing = missing | clan_members
    if not missing:
        return None

    links = await bot.link_client.get_links(*list(missing.keys()))
    links = dict(links)

    players = await bot.get_players(tags=list(missing.keys()), use_cache=True)

    missing_text_list = []
    missing_text = ''
    for full_player in sorted(players, key=lambda x: (-x.town_hall, x.name)):
        if full_player.town_hall <= 5:
            continue

        discord_id = links.get(full_player.tag, 0)
        player = missing.get(full_player.tag)
        if isinstance(player, coc.ClanMember):
            num_missing = f'(0/6)'
        else:
            num_missing = f'({(player.attack_limit + player.bonus_attack_limit) - player.attack_count}/{(player.attack_limit + player.bonus_attack_limit)})'
        discord_user = await server.getch_member(discord_id)
        if len(missing_text) + len(custom_text) + 150 >= 2000:
            missing_text_list.append(missing_text)
            missing_text = ''

        if discord_user is None:
            missing_text += f'{num_missing} {bot.fetch_emoji(full_player.town_hall)}{player.name} | {full_player.tag}\n'
        else:
            missing_text += (
                f'{num_missing} {bot.fetch_emoji(full_player.town_hall)}{player.name} | {discord_user.mention}\n'
            )

    if missing_text != '':
        missing_text_list.append(missing_text)

    time = reminder_time
    if not manual_send:
        time = f"{str(reminder_time).replace('hr', '')} Hours"

    for text in missing_text_list:
        reminder_text = (
            f'**{clan.name} Raid Weekend\n'
            f'{bot.emoji.clock}{time} Remaining\n'
            f'{bot.emoji.wood_swords}Min {attack_threshold} Attacks Required**\n'
            f'{missing_text}'
        )
        if text == missing_text_list[-1]:
            reminder_text += f'\n{custom_text}'
        try:
            await channel.send(content=reminder_text)
        except Exception:
            pass


async def clan_games_reminder(bot: CustomClient, reminder_time):
    for reminder in await bot.reminders.find({'$and': [{'type': 'Clan Games'}, {'time': reminder_time}]}).to_list(
        length=None
    ):
        reminder = Reminder(bot=bot, data=reminder)
        if reminder.server_id not in bot.OUR_GUILDS:
            continue

        try:
            channel = await bot.getch_channel(reminder.channel_id)
        except (disnake.NotFound, disnake.Forbidden):
            await reminder.delete()
            continue

        server = await bot.getch_guild(reminder.server_id)
        if server is None:
            continue

        clan = await bot.getClan(clan_tag=reminder.clan_tag)
        if clan is None:
            continue

        missing = {}
        member_points = {}
        for stat in await bot.player_stats.find({f'tag': {'$in': [member.tag for member in clan.members]}}).to_list(
            length=None
        ):
            points = stat.get('clan_games', {}).get(f'{bot.gen_games_season()}', {}).get('points', 0)
            if points < reminder.point_threshold:
                missing[stat.get('tag')] = coc.utils.get(clan.members, tag=stat.get('tag'))
                member_points[stat.get('tag')] = points

        if not missing:
            continue
        links = await bot.link_client.get_links(*list(missing.keys()))

        missing_text = ''
        for player_tag, discord_id in links:
            player = missing.get(player_tag)
            member = disnake.utils.get(server.members, id=discord_id)
            if member is None:
                missing_text += f'({member_points.get(player_tag)}/4000) {player.name} | {player_tag}\n'
            else:
                missing_text += f'({member_points.get(player_tag)}/4000) {player.name} | {member.mention}\n'
        time = str(reminder_time).replace('hr', '')
        badge = await bot.create_new_badge_emoji(url=clan.badge.url)
        reminder_text = (
            f'**{badge}{clan.name} (Clan Games)\n{time} Hours Left, Min {reminder.point_threshold} Points**\n'
            f'{missing_text}'
            f'\n{reminder.custom_text}'
        )

        try:
            await channel.send(content=reminder_text)
        except:
            pass


async def inactivity_reminder(bot: CustomClient):
    for reminder in await bot.reminders.find({'type': 'inactivity'}).to_list(length=None):
        reminder = Reminder(bot=bot, data=reminder)
        if reminder.server_id not in bot.OUR_GUILDS:
            continue

        try:
            channel = await bot.getch_channel(reminder.channel_id)
        except (disnake.NotFound, disnake.Forbidden):
            await reminder.delete()
            continue
        server = await bot.getch_guild(reminder.server_id)
        if server is None:
            continue

        clan = await bot.getClan(clan_tag=reminder.clan_tag)
        if clan is None:
            continue

        seconds_inactive = int(str(reminder.time).replace('hr', '')) * 60 * 60
        max_diff = 30 * 60  # time in seconds between runs
        now = datetime.datetime.now(tz=utc)
        clan_members = [member.tag for member in clan.members]
        clan_members_stats = await bot.player_stats.find({f'tag': {'$in': clan_members}}).to_list(length=None)
        inactive_tags = []
        names = {}
        for stat in clan_members_stats:
            last_online = stat.get('last_online')
            if last_online is None:
                continue
            lo_time = datetime.datetime.fromtimestamp(float(last_online), tz=utc)
            passed_time = (now - lo_time).total_seconds()
            if passed_time - seconds_inactive >= 0 and passed_time - seconds_inactive <= max_diff:
                inactive_tags.append(stat.get('tag'))
                try:
                    names[stat.get('tag')] = stat.get('name')
                except:
                    names[stat.get('tag')] = coc.utils.get(clan.members, tag=stat.get('tag')).name

        if not inactive_tags:
            continue
        links = await bot.link_client.get_links(*inactive_tags)
        inactive_text = ''
        for player_tag, discord_id in links:
            name = names.get(player_tag)
            member = await server.getch_member(discord_id)
            if member is None:
                inactive_text += f'{name} | {player_tag}\n'
            else:
                inactive_text += f'{name} | {member.mention}\n'
        time = str(reminder.time).replace('hr', '')
        badge = await bot.create_new_badge_emoji(url=clan.badge.url)
        reminder_text = (
            f'**{badge}{clan.name}\nPlayers Inactive for {time}Hours**\n' f'{inactive_text}' f'\n{reminder.custom_text}'
        )
        try:
            await channel.send(content=reminder_text)
        except:
            pass


async def roster_reminder(bot: CustomClient):
    pipeline = [
        {'$match': {'type': 'roster'}},
        {
            '$lookup': {
                'from': 'rosters',
                'localField': 'roster',
                'foreignField': '_id',
                'as': 'roster',
            }
        },
        {'$set': {'roster': {'$first': '$roster'}}},
    ]
    for reminder in await bot.reminders.aggregate(pipeline=pipeline).to_list(length=None):
        reminder = Reminder(bot=bot, data=reminder)
        if reminder.server_id not in bot.OUR_GUILDS:
            continue
        if not reminder.roster.is_valid or reminder.time is None or len(reminder.roster.players) == 0:
            continue

        try:
            channel = await bot.getch_channel(reminder.channel_id)
        except (disnake.NotFound, disnake.Forbidden):
            await reminder.delete()
            continue

        server = await bot.getch_guild(reminder.server_id)
        if server is None:
            continue

        time = reminder.time.replace('hr', '')
        seconds_before_to_ping = int(float(time) * 3600)

        max_diff = 2 * 60  # time in seconds between runs
        now = datetime.datetime.now(tz=utc)
        roster_time = datetime.datetime.fromtimestamp(float(reminder.roster.time), tz=utc)
        time_until_time = (roster_time - now).total_seconds()
        # goes negative if now >= time
        # gets smaller as we get closer

        # we want to ping when we are closer to the time than further, so when seconds_before
        # larger - smaller >= 0
        # smaller - larger <= 0
        if seconds_before_to_ping - time_until_time >= 0 and seconds_before_to_ping - time_until_time <= max_diff:
            members = []
            if reminder.ping_type == 'All Roster Members':
                members = reminder.roster.players
            elif reminder.ping_type == 'Not in Clan':
                members = await reminder.roster.missing_list(reverse=False)
            elif reminder.ping_type == 'Subs Only':
                members = [p for p in reminder.roster.players if p.get('sub', False)]

            if not members:
                continue
            links = await bot.link_client.get_links(*[p.get('tag') for p in members])
            missing_text_list = []
            text = ''
            for player_tag, discord_id in links:
                name = next(
                    (player for player in members if player.get('tag') == player_tag),
                    {},
                )
                name = name.get('name')
                member = await server.getch_member(discord_id)
                if len(text) + len(reminder.custom_text) + 150 >= 2000:
                    missing_text_list.append(text)
                    text = ''
                if member is None:
                    text += f'{name} | {player_tag}\n'
                else:
                    text += f'{name} | {member.mention}\n'

            if text != '':
                missing_text_list.append(text)
            badge = await bot.create_new_badge_emoji(url=reminder.roster.clan_badge)
            for text in missing_text_list:
                reminder_text = (
                    f'**{badge}{reminder.roster.clan_name} | {reminder.roster.alias} | {bot.timestamp(reminder.roster.time).relative}**\n\n'
                    f'{text}'
                )
                buttons = []
                if text == missing_text_list[-1]:
                    reminder_text += f'\n{reminder.custom_text}'
                    button = disnake.ui.Button(
                        label='Clan Link',
                        emoji='🔗',
                        style=disnake.ButtonStyle.url,
                        url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{reminder.roster.roster_result.get('clan_tag').strip('#')}",
                    )
                    buttons = [disnake.ui.ActionRow(button)]
                try:
                    await channel.send(content=reminder_text, components=buttons)
                except:
                    pass
