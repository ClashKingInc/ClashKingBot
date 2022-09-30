from disnake.ext import commands
import disnake
from coc import utils
from datetime import datetime
import datetime as dt
import pytz
utc = pytz.utc

from CustomClasses.CustomBot import CustomClient

class VoiceCountdowns(commands.Cog, name="Statbar Setup"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="voice-statbar", description="Setup a voice countdown/statbar")
    async def voice_setup(self, ctx: disnake.ApplicationCommandInteraction, type=commands.Param(choices=["CWL", "Clan Games", "Raid Weekend", "EOS"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)


        time_ = await self.calculate_time(type)

        try:
            if type == "Clan Games":
                channel = await ctx.guild.create_voice_channel(name=f"CG {time_}")
            elif type == "Raid Weekend":
                channel = await ctx.guild.create_voice_channel(name=f"Raids {time_}")
            else:
                channel = await ctx.guild.create_voice_channel(name=f"{type} {time_}")
        except disnake.Forbidden:
            embed = disnake.Embed(description="Bot requires admin to create & set permissions for channel.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        overwrite = disnake.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.connect = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        if type == "CWL":
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"cwlCountdown": channel.id}})
        elif type == "Clan Games":
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"gamesCountdown": channel.id}})
        elif type == "Raid Weekend":
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"raidCountdown": channel.id}})
        else:
            await self.bot.server_db.update_one({"server": ctx.guild.id}, {'$set': {"eosCountdown": channel.id}})

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
                    text = f"ends {int(hrs)}H {int(mins)}M"
                    if int(hrs) == 0:
                        text = f"ends in {int(mins)}M"
                else:
                    text = f"ends {int(days)}D {int(hrs)}H"
            else:
                time_left = first - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"in {int(hrs)}H {int(mins)}M"
                    if int(hrs) == 0:
                        text = f"in {int(mins)}M"
                else:
                    text = f"in {int(days)}D {int(hrs)}H"

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
                    text = f"ends {int(hrs)}H {int(mins)}M"
                    if int(hrs) == 0:
                        text = f"ends in {int(mins)}M"
                else:
                    text = f"ends {int(days)}D {int(hrs)}H"
            else:
                time_left = first - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"in {int(hrs)}H {int(mins)}M"
                    if int(hrs) == 0:
                        text = f"in {int(mins)}M"
                else:
                    text = f"in {int(days)}D {int(hrs)}H"

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
                end = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days= (7 - current_dayofweek))
                time_left = end - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"end {int(hrs)}H {int(mins)}M"
                    if int(hrs) == 0:
                        text = f"end in {int(mins)}M"
                else:
                    text = f"end {int(days)}D {int(hrs)}H"
            else:
                first = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(4 - current_dayofweek))
                time_left = first - now
                secs = time_left.total_seconds()
                days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
                hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
                mins, secs = divmod(secs, secs_per_min := 60)
                if int(days) == 0:
                    text = f"in {int(hrs)}H {int(mins)}M"
                    if int(hrs) == 0:
                        text = f"in {int(mins)}M"
                else:
                    text = f"in {int(days)}D {int(hrs)}H"

        elif type == "EOS":
            end = utils.get_season_end().replace(tzinfo=utc)
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)

            if int(days) == 0:
                text = f"in {int(hrs)}H {int(mins)}M"
                if int(hrs) == 0:
                    text = f"in {int(mins)}M"
            else:
                text = f"in {int(days)}D {int(hrs)}H "

        return text


def setup(bot: CustomClient):
    bot.add_cog(VoiceCountdowns(bot))