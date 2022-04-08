from disnake.ext import commands, tasks
import disnake
from utils.clash import client, coc_client

from datetime import datetime

import pytz
utc = pytz.utc

usafam = client.usafam
server = usafam.server
clans = usafam.clans


class VoiceCountdowns(commands.Cog, name="Statbar Setup"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_update.start()

    def cog_unload(self):
        self.voice_update.cancel()

    @tasks.loop(seconds=600)
    async def voice_update(self):
        results = server.find()
        limit = await server.count_documents(filter={})
        for r in await results.to_list(length=limit):
            channel = r.get("cwlCountdown")
            servers = r.get("server")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    time_ = await self.calculate_time("CWL")
                    await channel.edit(name=f"CWL {time_}")
                except (disnake.NotFound, disnake.Forbidden):
                    await server.update_one({"server": servers}, {'$set': {"cwlCountdown": None}})

            channel = r.get("gamesCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    time_ = await self.calculate_time("Clan Games")
                    await channel.edit(name=f"CG {time_}")
                except (disnake.NotFound, disnake.Forbidden):
                    await server.update_one({"server": servers}, {'$set': {"gamesCountdown": None}})

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

    @commands.slash_command(name="voice-statbar", description="Setup a voice countdown/statbar")
    async def voice_setup(self, ctx: disnake.ApplicationCommandInteraction, type=commands.Param(choices=["CWL", "Clan Games", "Clan Member Count"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if type != "Clan Member Count":
            time_ = await self.calculate_time(type)

        if type == "Clan Games":
            channel = await ctx.guild.create_voice_channel(name=f"CG {time_}")
        elif type == "CWL":
            channel = await ctx.guild.create_voice_channel(name=f"{type} {time_}")
        else:
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})
            list = []
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                list.append(tag)
            total = 0
            async for clan in coc_client.get_clans(list):
                total+=len(clan.members)
            channel = await ctx.guild.create_voice_channel(name=f"{total} Clan Members")

        overwrite = disnake.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.connect = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        if type == "CWL":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"cwlCountdown": channel.id}})
        elif type == "CWL":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"gamesCountdown": channel.id}})
        else:
            await server.update_one({"server": ctx.guild.id}, {'$set': {"memberCount": channel.id}})

        embed = disnake.Embed(description=f"{type} Stat Bar Created",
                              color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)


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
            end = datetime(year, month, 10, hour=8, tzinfo=utc)
            if (day >= 1 and day<=10):
                if (day == 1 and hour < 8) or (day == 10 and hour >= 8):
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

        else:
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
                first = datetime(year, month+1, 22, hour=8, tzinfo=utc)

            if day >= 29:
                first = datetime(year, month+1, 22, hour=8, tzinfo=utc)

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


        return text

def setup(bot: commands.Bot):
    bot.add_cog(VoiceCountdowns(bot))