import datetime
import coc
import disnake
import pytz
utc = pytz.utc
from disnake.ext import commands
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from Clan.ClanResponder import clan_raid_weekend_raid_stats, clan_raid_weekend_donation_stats
from ImageGen import ClanCapitalResult as capital_gen


class reminders(commands.Cog, name="Reminder Cron"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #ends at 7 am monday
        scheduler.add_job(self.send_boards, "cron", day_of_week="mon", hour=7, minute=3, misfire_grace_time=None)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["1 hr"], day_of_week="mon", hour=6, misfire_grace_time=None)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["6 hr"], day_of_week="mon", hour=1, misfire_grace_time=None)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["12 hr"], day_of_week="sun", hour=19, misfire_grace_time=None)
        scheduler.add_job(self.clan_capital_reminder, "cron", args=["24 hr"], day_of_week="sun", hour=7, misfire_grace_time=None)

        #22nd to 28th of every month, at 8am
        scheduler.add_job(self.clan_games_reminder, "cron", args=["144 hr"], day=22, hour=8, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["120 hr"], day=23, hour=8, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["96 hr"], day=24, hour=8, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["72 hr"], day=25, hour=8, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["48 hr"], day=26, hour=8, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["36 hr"], day=26, hour=20, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["24 hr"], day=27, hour=8, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["12 hr"], day=27, hour=20, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["6 hr"], day=28, hour=2, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["4 hr"], day=28, hour=4, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["2 hr"], day=28, hour=6, misfire_grace_time=None)
        scheduler.add_job(self.clan_games_reminder, "cron", args=["1 hr"], day=28, hour=7, misfire_grace_time=None)

        scheduler.add_job(self.inactivity_reminder, 'interval', minutes=30, misfire_grace_time=None)

    #REMINDER SENDING UTILS
    async def war_reminder(self, clan_tag, reminder_time):
        war = await self.bot.get_clanwar(clanTag=clan_tag)
        if war is None:
            return
        missing = {}; names = {}; ths = {}
        for player in war.members:
            if player not in war.opponent.members:
                if len(player.attacks) < war.attacks_per_member:
                    missing[player.tag] = war.attacks_per_member - len(player.attacks)
                    names[player.tag] = player.name
                    ths[player.tag] = player.town_hall

        tags= list(missing.keys())
        if not missing:
            return
        links = await self.bot.link_client.get_links(*tags)
        all_reminders = self.bot.reminders.find({"$and": [
            {"clan": clan_tag},
            {"type": "War"},
            {"time": f"{reminder_time} hr"}
        ]})
        limit = await self.bot.reminders.count_documents(filter={"$and": [
            {"clan": clan_tag},
            {"type": "War"},
            {"time": f"{reminder_time} hr"}
        ]})
        for reminder in await all_reminders.to_list(length=limit):
            custom_text = reminder.get("custom_text")
            if custom_text is None:
                custom_text = ""
            else:
                custom_text = "\n" + custom_text
            channel = reminder.get("channel")
            try:
                channel = await self.bot.fetch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": clan_tag},
                    {"server": reminder.get("server")},
                    {"time" : f"{reminder_time} hr"},
                    {"type": "War"}
                ]})
            server = self.bot.get_guild(reminder.get("server"))
            if server is None:
                continue
            missing_text_list = []
            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if len(missing_text) + len(custom_text) + 100 >= 2000:
                    missing_text_list.append(missing_text)
                    missing_text = ""
                if member is None:
                    missing_text += f"{num_missing} hits- {self.bot.fetch_emoji(ths[player_tag])}{name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing} hits- {self.bot.fetch_emoji(ths[player_tag])}{name} | {member.mention}\n"
            if missing_text != "":
                missing_text_list.append(missing_text)
            badge = await self.bot.create_new_badge_emoji(url=war.clan.badge.url)
            for text in missing_text_list:
                reminder_text = f"**{reminder_time} Hours Remaining in War**\n" \
                                f"**{badge}{war.clan.name} vs {war.opponent.name}**\n\n" \
                                f"{text}"
                if text == missing_text_list[-1]:
                    reminder_text += f"{custom_text}"
                await channel.send(content=reminder_text)

    async def clan_capital_reminder(self, reminder_time):
        all_reminders = self.bot.reminders.find({"$and": [
            {"type": "Clan Capital"},
            {"time": reminder_time}
        ]})
        for reminder in await all_reminders.to_list(length=10000):
            custom_text = reminder.get("custom_text")
            custom_text = "" if custom_text is None else "\n" + custom_text
            channel = reminder.get("channel")
            try:
                channel = await self.bot.getch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": reminder.get("clan")},
                    {"server": reminder.get("server")},
                    {"time": f"{reminder_time}"},
                    {"type": "Clan Capital"}
                ]})
                continue
            server = self.bot.get_guild(reminder.get("server"))
            if server is None:
                continue
            clan = await self.bot.getClan(clan_tag=reminder.get("clan"))
            if clan is None:
                continue
            weekend = gen_raid_weekend_datestrings(1)[0]
            raid_log_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot)
            if raid_log_entry is None:
                continue

            missing = {}
            names = {}
            max = {}
            for member in raid_log_entry.members:
                if member.attack_count < (member.attack_limit + member.bonus_attack_limit):
                    names[member.tag] = member.name
                    missing[member.tag] = (member.attack_limit + member.bonus_attack_limit) - member.attack_count
                    max[member.tag] = (member.attack_limit + member.bonus_attack_limit)

            tags = list(missing.keys())
            if not missing:
                continue
            links = await self.bot.link_client.get_links(*tags)
            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                max_do = max[player_tag]
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"{num_missing} raids- {name} | {player_tag}\n"
                else:
                    missing_text += f"{num_missing} raids- {name} | {member.mention}\n"
            time = str(reminder_time).replace("hr", "")
            badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            reminder_text = f"**{badge}{clan.name}\n{time} Hours Remaining in Raid Weekend**\n" \
                                f"{missing_text}" \
                                f"{custom_text}"
            try:
                await channel.send(content=reminder_text)
            except:
                continue

    async def send_boards(self):
        tracked = self.bot.clan_db.find({"clan_capital" : {"$ne" : None}})
        limit = await self.bot.clan_db.count_documents(filter={"clan_capital" : {"$ne" : None}})
        for cc in await tracked.to_list(length=limit):
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue
            try:
                clancapital_channel = await self.bot.getch_channel(clancapital_channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": cc.get("tag")},
                    {"server": cc.get("server")}
                ]}, {'$set': {"clan_capital": None}})
                continue

            clan = await self.bot.getClan(clan_tag=cc.get("tag"))
            if clan is None:
                continue
            weekend = gen_raid_weekend_datestrings(2)[1]
            raid_log_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot)
            if raid_log_entry is None:
                continue
            file = await capital_gen.generate_raid_result_image(raid_entry=raid_log_entry, clan=clan)
            (raid_embed, total_looted, total_attacks) = clan_raid_weekend_raid_stats(clan=clan, raid_log_entry=raid_log_entry)
            donation_embed = await clan_raid_weekend_donation_stats(clan=clan, weekend=weekend, bot=self.bot)

            try:
                await clancapital_channel.send(embed=raid_embed)
                await clancapital_channel.send(embed=donation_embed)
                await clancapital_channel.send(file=file)
            except:
                continue

    async def clan_games_reminder(self, reminder_time):
        all_reminders = self.bot.reminders.find({"$and": [
            {"type": "Clan Games"},
            {"time": reminder_time}
        ]})
        for reminder in await all_reminders.to_list(length=10000):
            custom_text = reminder.get("custom_text")
            custom_text = "" if custom_text is None else "\n" + custom_text
            channel = reminder.get("channel")
            try:
                channel = await self.bot.getch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": reminder.get("clan")},
                    {"server": reminder.get("server")},
                    {"time": f"{reminder_time}"},
                    {"type": "Clan Games"}
                ]})
                continue
            server = self.bot.get_guild(reminder.get("server"))
            if server is None:
                continue
            clan = await self.bot.getClan(clan_tag=reminder.get("clan"))
            if clan is None:
                continue

            point_threshold = reminder.get("point_threshold")
            clan_member_tags = [member.tag for member in clan.members]
            clan_members_stats = await self.bot.player_stats.find({f"tag": {"$in": clan_member_tags}}).to_list(length=100)
            current_season = self.bot.gen_season_date()
            diff_days = datetime.datetime.utcnow().replace(tzinfo=utc) - coc.utils.get_season_end().replace(tzinfo=utc)
            if diff_days.days <= 3:
                sea = coc.utils.get_season_start().replace(tzinfo=utc).date()
                current_season = f"{sea.year}-{sea.month}"
            under_point_tags = []
            names = {}
            missing = {}
            for stat in clan_members_stats:
                points = 0
                try:
                    points = stat.get("clan_games").get(f"{current_season}").get("points")
                except:
                    pass
                if points < point_threshold:
                    under_point_tags.append(stat.get("tag"))
                    missing[stat.get("tag")] = (point_threshold - points)
                    try:
                        names[stat.get("tag")] = stat.get("name")
                    except:
                        names[stat.get("tag")] = coc.utils.get(clan.members, tag=stat.get("tag")).name

            if not under_point_tags:
                continue
            links = await self.bot.link_client.get_links(*under_point_tags)

            missing_text = ""
            for player_tag, discord_id in links:
                num_missing = missing[player_tag]
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    missing_text += f"({num_missing}/{point_threshold})- {name} | {player_tag}\n"
                else:
                    missing_text += f"({num_missing}/{point_threshold})- {name} | {member.mention}\n"
            time = str(reminder_time).replace("hr", "")
            badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            reminder_text = f"**{badge}{clan.name}\n{time} Hours Remaining in Clan Games**\n" \
                            f"*Points needed to hit {point_threshold}points*\n" \
                                f"{missing_text}" \
                                f"{custom_text}"
            try:
                await channel.send(content=reminder_text)
            except:
                continue

    async def inactivity_reminder(self):
        all_reminders = self.bot.reminders.find({"$and": [
            {"type": "inactivity"}
        ]})
        for reminder in await all_reminders.to_list(length=10000):
            custom_text = reminder.get("custom_text")
            custom_text = "" if custom_text is None else "\n" + custom_text
            channel = reminder.get("channel")
            reminder_time = reminder.get("time")
            try:
                channel = await self.bot.getch_channel(channel)
            except (disnake.NotFound, disnake.Forbidden):
                await self.bot.reminders.delete_one({"$and": [
                    {"clan": reminder.get("clan")},
                    {"server": reminder.get("server")},
                    {"time": f"{reminder_time}"},
                    {"type": "inactivity"}
                ]})
                continue
            server = self.bot.get_guild(reminder.get("server"))
            if server is None:
                continue
            clan = await self.bot.getClan(clan_tag=reminder.get("clan"))
            if clan is None:
                continue

            seconds_inactive = int(str(reminder_time).replace("hr", "")) * 60 * 60
            max_diff = 30 * 60 #time in seconds between runs
            now = datetime.datetime.now(tz=utc)
            clan_members = [member.tag for member in clan.members]
            clan_members_stats = await self.bot.player_stats.find({f"tag": {"$in" : clan_members}}).to_list(length=100)
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
            links = await self.bot.link_client.get_links(*inactive_tags)
            inactive_text = ""
            for player_tag, discord_id in links:
                name = names[player_tag]
                member = disnake.utils.get(server.members, id=discord_id)
                if member is None:
                    inactive_text += f"{name} | {player_tag}\n"
                else:
                    inactive_text += f"{name} | {member.mention}\n"
            time = str(reminder_time).replace("hr", "")
            badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
            reminder_text = f"**{badge}{clan.name}\nPlayers Inactive for {time}Hours**\n" \
                            f"{inactive_text}" \
                            f"{custom_text}"
            try:
                await channel.send(content=reminder_text)
            except:
                continue


def setup(bot: CustomClient):
    bot.add_cog(reminders(bot))
