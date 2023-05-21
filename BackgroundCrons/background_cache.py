import pytz
import os
import time
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands

utc = pytz.utc
EMAIL = os.getenv("LEGEND_EMAIL")
PASSWORD = os.getenv("LEGEND_PW")

class BackgroundCache(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #bot.loop.run_until_complete(self.player_cache())

    async def player_cache(self):
        print("here cache")
        while True:
            r = time.time()
            spot = 0
            async for document in await self.bot.player_cache.find({}).to_list(length=None):
                del document["_id"]
                self.bot.player_cache_dict[document["tag"]] = document
                if spot % 25000:
                    print(f"{25000 * spot} docs")
            print(f"done cache, {time.time() - r} sec")

def setup(bot: CustomClient):

    bot.add_cog(BackgroundCache(bot))
