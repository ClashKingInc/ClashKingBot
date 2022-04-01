from discord.ext import commands, tasks
import discord
from discord_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow
from utils.clashClient import client
from main import check_commands

from datetime import datetime
from datetime import timedelta

from pytz import timezone
import pytz
utc = pytz.utc

usafam = client.usafam
server = usafam.server


class VoiceCountdowns(commands.Cog):

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
                except (discord.NotFound, discord.Forbidden):
                    await server.update_one({"server": servers}, {'$set': {"cwlCountdown": None}})

            channel = r.get("gamesCountdown")
            if channel is not None:
                try:
                    channel = await self.bot.fetch_channel(channel)
                    time_ = await self.calculate_time("Clan Games")
                    await channel.edit(name=f"CG {time_}")
                except (discord.NotFound, discord.Forbidden):
                    await server.update_one({"server": servers}, {'$set': {"gamesCountdown": None}})

    @commands.group(name="countdown",pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def voice(self, ctx):
        pass

    @voice.group(name="setup", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def voice_setup(self, ctx):
        embed = discord.Embed(title=f"Voice Channel Countdown Setup",
                              description="Choose a countdown to setup.",
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())


        select1 = create_select(
            options=[
                create_select_option("CWL", value=f"CWL"),
                create_select_option("Clan Games", value=f"Clan Games"),
                create_select_option("Cancel", value=f"Cancel")
            ],
            placeholder="Choose countdown type.",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)
        msg = await ctx.send(embed=embed, components=[action_row])

        chose = False
        while chose == False:
            try:
                res = await wait_for_component(self.bot, components=action_row, messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            chose = res.values[0]
            # print(chose)

            if chose == "Cancel":
                embed = discord.Embed(description=f"Sorry to hear that. Canceling the command now.",
                                      color=discord.Color.green())
                embed.set_thumbnail(url=ctx.guild.icon_url_as())
                return await msg.edit(embed=embed,
                                      components=[])

        time_ = await self.calculate_time(chose)

        if chose == "Clan Games":
            channel = await ctx.guild.create_voice_channel(name=f"CG {time_}")
        else:
            channel = await ctx.guild.create_voice_channel(name=f"{chose} {time_}")

        overwrite = discord.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.connect = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        if chose == "CWL":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"cwlCountdown": channel.id}})
        else:
            await server.update_one({"server": ctx.guild.id}, {'$set': {"gamesCountdown": channel.id}})

        embed = discord.Embed(description=f"{chose} Countdown Created",
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())
        await msg.edit(embed=embed, components=[])


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