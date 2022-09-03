from disnake.ext import commands, tasks
import disnake

from datetime import datetime
from datetime import timedelta
from main import scheduler
import pytz
utc = pytz.utc

from CustomClasses.CustomBot import CustomClient

class VoiceStatCron(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.voice_update, 'interval', minutes=10)

    async def voice_update(self):
        results = self.bot.server_db.find()
        limit = await self.bot.server_db.count_documents(filter={})
        for r in await results.to_list(length=limit):
            channel = r.get("cwlCountdown")
            #print(channel)
            servers = r.get("server")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    time_ = await self.calculate_time("CWL")
                    await channel.edit(name=f"CWL {time_}")
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": servers}, {'$set': {"cwlCountdown": None}})

            channel = r.get("gamesCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    time_ = await self.calculate_time("Clan Games")
                    await channel.edit(name=f"CG {time_}")
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": servers}, {'$set': {"gamesCountdown": None}})

            channel = r.get("raidCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    time_ = await self.calculate_time("Raid Weekend")
                    await channel.edit(name=f"Raids {time_}")
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": servers}, {'$set': {"raidCountdown": None}})

            '''
            channel = r.get("memberCount")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    tracked = clans.find({"server": servers})
                    limit = await clans.count_documents(filter={"server": servers})
                    list = []
                    for tClan in await tracked.to_list(length=limit):
                        tag = tClan.get("tag")
                        list.append(tag)
                    total = 0
                    async for clan in coc_client.get_clans(list):
                        total+=len(clan.members)
                    await channel.edit(name=f"{total} Clan Members")
                except (disnake.NotFound, disnake.Forbidden):
                    await server.update_one({"server": servers}, {'$set': {"memberCount": None}})
            '''

    async def calculate_time(self, type):
        text = ""
        now = datetime.utcnow().replace(tzinfo=utc)
        year = now.year
        month = now.month
        day = now.day
        hour = now.hour
        if type == "CWL":
            is_cwl = True
            if day == 1:
                first = datetime(year, month, 1, hour=8, tzinfo=utc)
            else:
                first = datetime(year, month + 1, 1, hour=8, tzinfo=utc)
            end = datetime(year, month, 11, hour=8, tzinfo=utc)
            if (day >= 1 and day <= 10):
                if (day == 1 and hour < 8) or (day == 11 and hour >= 8):
                    is_cwl = False
                else:
                    is_cwl = True
            else:
                is_cwl = False

            if is_cwl:
                time_left = end - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"ends {int(hrs)} Hours {int(mins)} Mins"
                    if int(hrs) == 0:
                        text = f"ends {int(mins)} Minutes"
                else:
                    text = f"ends {int(days)} Days {int(hrs)} Hours"
            else:
                time_left = first - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"in {int(hrs)} Hours {int(mins)} Mins"
                    if int(hrs) == 0:
                        text = f"in {int(mins)} Minutes"
                else:
                    text = f"in {int(days)} Days {int(hrs)} Hours"

        elif type == "Clan Games":
            is_games = True
            first = datetime(year, month, 22, hour=8, tzinfo=utc)
            end = datetime(year, month, 28, hour=8, tzinfo=utc)
            if (day >= 22 and day <= 28):
                if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
                    is_games = False
                else:
                    is_games = True
            else:
                is_games = False

            if day == 28 and hour >= 8:
                first = datetime(year, month + 1, 22, hour=8, tzinfo=utc)

            if day >= 29:
                first = datetime(year, month + 1, 22, hour=8, tzinfo=utc)

            if is_games:
                time_left = end - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"ends {int(hrs)} Hours {int(mins)} Mins"
                    if int(hrs) == 0:
                        text = f"ends {int(mins)} Minutes"
                else:
                    text = f"ends {int(days)} Days {int(hrs)} Hours"
            else:
                time_left = first - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"in {int(hrs)} Hours {int(mins)} Mins"
                    if int(hrs) == 0:
                        text = f"in {int(mins)} Minutes"
                else:
                    text = f"in {int(days)} Days {int(hrs)} Hours"

        elif type == "Raid Weekend":
            now = datetime.utcnow().replace(tzinfo=utc)
            current_dayofweek = now.weekday()
            if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
                    current_dayofweek == 0 and now.hour < 7):
                if current_dayofweek == 0:
                    current_dayofweek = 7
                is_raids = True
            else:
                is_raids = False

            if is_raids:
                end = datetime(year, month, day, hour=7, tzinfo=utc) + timedelta((7 - current_dayofweek))
                time_left = end - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"ends {int(hrs)} Hours {int(mins)} Mins"
                    if int(hrs) == 0:
                        text = f"ends {int(mins)} Minutes"
                else:
                    text = f"ends {int(days)} Days {int(hrs)} Hours"
            else:
                first = datetime(year, month, day, hour=7, tzinfo=utc) + timedelta((4 - current_dayofweek))
                time_left = first - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"in {int(hrs)} Hours {int(mins)} Mins"
                    if int(hrs) == 0:
                        text = f"in {int(mins)} Minutes"
                else:
                    text = f"in {int(days)} Days {int(hrs)} Hours"

        return text

def setup(bot: CustomClient):
    bot.add_cog(VoiceStatCron(bot))