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
        #bot.loop.run_until_complete(self.player_cache())
        self.guilds.start()

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

    @tasks.loop(seconds=60)
    async def guilds(self):
        guild_fetch = await self.bot.server_db.distinct("server")
        if self.bot.user.public_flags.verified_bot:
            all_guilds = [str(g) for g in guild_fetch]
            await self.bot.server_db.update_one({"server" : 923764211845312533}, {"$set" : {"all_servers" : all_guilds}})
        else:
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
