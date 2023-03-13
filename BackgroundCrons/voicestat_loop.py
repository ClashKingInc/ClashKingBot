from disnake.ext import commands, tasks
import disnake
from utils.General import calculate_time
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
            server = r.get("server")
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel)
                    time_ = await calculate_time("CWL")
                    prev_name = channel.name
                    text = f"CWL {time_}"
                    if "|" in prev_name:
                        custom = prev_name.split("|")[0]
                        text = f"{custom}| {text}"
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": server}, {'$set': {"cwlCountdown": None}})

            channel = r.get("gamesCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel)
                    time_ = await calculate_time("Clan Games")
                    prev_name = channel.name
                    text = f"CG {time_}"
                    if "|" in prev_name:
                        custom = prev_name.split("|")[0]
                        text = f"{custom}| {text}"
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": server}, {'$set': {"gamesCountdown": None}})

            channel = r.get("raidCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel)
                    time_ = await calculate_time("Raid Weekend")
                    prev_name = channel.name
                    text = f"Raids {time_}"
                    if "|" in prev_name:
                        custom = prev_name.split("|")[0]
                        text = f"{custom}| {text}"
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": server}, {'$set': {"raidCountdown": None}})

            channel = r.get("eosCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.getch_channel(channel)
                    time_ = await calculate_time("EOS")
                    prev_name = channel.name
                    text = f"EOS {time_}"
                    if "|" in prev_name:
                        custom = prev_name.split("|")[0]
                        text = f"{custom}| {text}"
                    if text != channel.name:
                        await channel.edit(name=text)
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": server}, {'$set': {"eosCountdown": None}})


            channel = r.get("memberCount")
            if channel is not None:
                try:
                    clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": server})
                    results = await self.bot.player_stats.count_documents(filter = {"clan_tag": {"$in": clan_tags}})
                    await channel.edit(name=f"{results} Clan Members")
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.server_db.update_one({"server": server}, {'$set': {"memberCount": None}})




def setup(bot: CustomClient):
    bot.add_cog(VoiceStatCron(bot))

