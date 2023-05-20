import pytz
import os
import aiohttp

from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from main import scheduler

utc = pytz.utc
EMAIL = os.getenv("LEGEND_EMAIL")
PASSWORD = os.getenv("LEGEND_PW")

class BackgroundCache(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.player_cache, 'interval', minutes=5)

    async def player_cache(self):
        pass



def setup(bot: CustomClient):
    bot.add_cog(BackgroundCache(bot))
