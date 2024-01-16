import pytz
import os
import time
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands, tasks

utc = pytz.utc
EMAIL = os.getenv("LEGEND_EMAIL")
PASSWORD = os.getenv("LEGEND_PW")

class BackgroundCache(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.guilds.start()



    @tasks.loop(seconds=60)
    async def guilds(self):
        guild_fetch = await self.bot.server_db.distinct("server")
        if not self.bot.user.public_flags.verified_bot:
            guild_fetch = [guild.id for guild in self.bot.guilds if guild.id != 923764211845312533]
        x = guild_fetch
        if self.bot.user.public_flags.verified_bot:
            active_custom_bots = await self.bot.credentials.distinct("server")
            for bot in active_custom_bots:
                try:
                    x.remove(bot)
                except:
                    pass
        self.bot.OUR_GUILDS = set(x)


def setup(bot: CustomClient):

    bot.add_cog(BackgroundCache(bot))
