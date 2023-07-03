import datetime
import coc
import disnake

from pytz import utc
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from CustomClasses.CustomBot import CustomClient
from CustomClasses.ReminderClass import Reminder
from contextlib import suppress


async def war_reminder(bot: CustomClient, clan_tag, reminder_time):
    war = await bot.get_clanwar(clanTag=clan_tag)
    if war is None:
        return
    missing = {}; names = {}; ths = {}
    for player in war.clan.members:
        if len(player.attacks) < war.attacks_per_member:
            missing[player.tag] = war.attacks_per_member - len(player.attacks)
            names[player.tag] = player.name
            ths[player.tag] = player.town_hall

    tags= list(missing.keys())
    if not missing:
        return
    links = await bot.link_client.get_links(*tags)
    all_reminders = bot.reminders.find({"$and": [
        {"clan": clan_tag},
        {"type": "War"},
        {"time": f"{reminder_time} hr"}
    ]})
    for reminder in await all_reminders.to_list(length=None):
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

        missing_text_list = []
        missing_text = ""
        for player_tag, discord_id in links:
            num_missing = missing[player_tag]
            name = names[player_tag]
            member = disnake.utils.get(server.members, id=discord_id)
            if len(missing_text) + len(reminder.custom_text) + 100 >= 2000:
                missing_text_list.append(missing_text)
                missing_text = ""
            if member is None:
                missing_text += f"({num_missing}/{war.attacks_per_member}) {bot.fetch_emoji(ths[player_tag])}{name} | {player_tag}\n"
            else:
                missing_text += f"({num_missing}/{war.attacks_per_member}) {bot.fetch_emoji(ths[player_tag])}{name} | {member.mention}\n"

        if missing_text != "":
            missing_text_list.append(missing_text)
        badge = await bot.create_new_badge_emoji(url=war.clan.badge.url)
        for text in missing_text_list:
            reminder_text = f"**{reminder_time} Hours Remaining in War**\n" \
                            f"**{badge}{war.clan.name} vs {war.opponent.name}**\n\n" \
                            f"{text}"
            if text == missing_text_list[-1]:
                reminder_text += f"\n{reminder.custom_text}"
            with suppress:
                await channel.send(content=reminder_text)


async def clan_capital_reminder(bot:CustomClient, reminder_time):

    for reminder in await bot.reminders.find({"$and": [{"type": "Clan Capital"}, {"time": reminder_time}]}).to_list(length=None):
        reminder = Reminder(bot=bot, data=reminder)
        if reminder.server_id not in bot.OUR_GUILDS:
            continue

        try:
            channel = await bot.getch_channel(reminder.channel_id)
        except (disnake.NotFound, disnake.Forbidden):
            await reminder.delete()
            continue

        server = await bot.getch_guild(guild_id=reminder.server_id)
        if server is None:
            continue

        clan = await bot.getClan(clan_tag=reminder.clan_tag)
        if clan is None:
            continue
        weekend = gen_raid_weekend_datestrings(1)[0]
        raid_log_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=bot, limit=1)
        if raid_log_entry is None:
            continue

        missing = {}
        clan_members = {member.tag : member for member in clan.members}
        for member in raid_log_entry.members: #type: coc.RaidMember
            del clan_members[member.tag]
            if member.attack_count < reminder.attack_threshold:
                missing[member.tag] = member

        missing = missing | clan_members
        if not missing:
            continue

        links = await bot.link_client.get_links(*list(missing.keys()))

        missing_text = ""
        for player_tag, discord_id in links:
            player = missing.get(player_tag)
            if isinstance(player, coc.ClanMember):
                num_missing = f"(0/6)"
            else:
                num_missing = f"{(player.attack_limit + player.bonus_attack_limit) - player.attack_count}/{(player.attack_limit + player.bonus_attack_limit)})"
            discord_user = await server.getch_member(discord_id)
            if discord_user is None:
                missing_text += f"{num_missing} {player.name} | {player_tag}\n"
            else:
                missing_text += f"{num_missing} {player.name} | {discord_user.mention}\n"
        time = str(reminder_time).replace("hr", "")
        badge = await bot.create_new_badge_emoji(url=clan.badge.url)
        reminder_text = f"**{badge}{clan.name}(Raid Weekend)\n{time} Hours Left, Min {reminder.attack_threshold} Atk**\n" \
                        f"{missing_text}" \
                        f"\n{reminder.custom_text}"

        with suppress:
            await channel.send(content=reminder_text)


async def clan_games_reminder(bot: CustomClient, reminder_time):
    for reminder in await bot.reminders.find({"$and": [{"type": "Clan Games"}, {"time": reminder_time}]}).to_list(length=None):
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
        for stat in await bot.player_stats.find({f"tag": {"$in": [member.tag for member in clan.members]}}).to_list(length=None):
            points = stat.get("clan_games", {}).get(f"{bot.gen_games_season()}", {}).get("points", 0)
            if points < reminder.point_threshold:
                missing[stat.get("tag")] = coc.utils.get(clan.members, tag=stat.get("tag"))
                member_points[stat.get("tag")] = points


        if not missing:
            continue
        links = await bot.link_client.get_links(*list(missing.keys()))

        missing_text = ""
        for player_tag, discord_id in links:
            player = missing.get(player_tag)
            member = disnake.utils.get(server.members, id=discord_id)
            if member is None:
                missing_text += f"({member_points.get(player_tag)}/4000) {player.name} | {player_tag}\n"
            else:
                missing_text += f"({member_points.get(player_tag)}/4000) {player.name} | {member.mention}\n"
        time = str(reminder_time).replace("hr", "")
        badge = await bot.create_new_badge_emoji(url=clan.badge.url)
        reminder_text = f"**{badge}{clan.name} (Clan Games)\n{time} Hours Left, Min {reminder.point_threshold} Points**\n" \
                        f"{missing_text}" \
                        f"\n{reminder.custom_text}"

        with suppress:
            await channel.send(content=reminder_text)


async def inactivity_reminder(bot: CustomClient):

    for reminder in await bot.reminders.find({"type": "inactivity"}).to_list(length=None):
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

        seconds_inactive = int(str(reminder.time).replace("hr", "")) * 60 * 60
        max_diff = 30 * 60 #time in seconds between runs
        now = datetime.datetime.now(tz=utc)
        clan_members = [member.tag for member in clan.members]
        clan_members_stats = await bot.player_stats.find({f"tag": {"$in" : clan_members}}).to_list(length=None)
        inactive_tags = []
        names = {}
        for stat in clan_members_stats:
            last_online = stat.get("last_online")
            if last_online is None:
                continue
            lo_time = datetime.datetime.fromtimestamp(float(last_online), tz=utc)
            passed_time = (now - lo_time).total_seconds()
            if passed_time - seconds_inactive >= 0 and passed_time - seconds_inactive <= max_diff:
                inactive_tags.append(stat.get("tag"))
                try:
                    names[stat.get("tag")] = stat.get("name")
                except:
                    names[stat.get("tag")] = coc.utils.get(clan.members, tag=stat.get("tag")).name

        if not inactive_tags:
            continue
        links = await bot.link_client.get_links(*inactive_tags)
        inactive_text = ""
        for player_tag, discord_id in links:
            name = names.get(player_tag)
            member = await server.getch_member(discord_id)
            if member is None:
                inactive_text += f"{name} | {player_tag}\n"
            else:
                inactive_text += f"{name} | {member.mention}\n"
        time = str(reminder.time).replace("hr", "")
        badge = await bot.create_new_badge_emoji(url=clan.badge.url)
        reminder_text = f"**{badge}{clan.name}\nPlayers Inactive for {time}Hours**\n" \
                        f"{inactive_text}" \
                        f"\n{reminder.custom_text}"
        with suppress:
            await channel.send(content=reminder_text)

