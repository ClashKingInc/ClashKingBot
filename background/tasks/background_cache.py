
from classes.bot import CustomClient
from disnake.ext import commands, tasks


class BackgroundCache(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.guilds_store.start()



    @tasks.loop(seconds=60)
    async def guilds_store(self):
        if not self.bot.user.public_flags.verified_bot:
            guild_id_list = [guild.id for guild in self.bot.guilds]
            await self.bot.custom_bots.update_one({"token" : self.bot._config.bot_token}, {"$set" : {"server_ids" : guild_id_list}})
        else:
            guild_id_list = [guild.id for guild in self.bot.guilds]
        self.bot.OUR_GUILDS = set(guild_id_list)

    @guilds_store.before_loop
    async def before_guilds_store(self):
        await self.bot.wait_until_ready()


def setup(bot: CustomClient):

    bot.add_cog(BackgroundCache(bot))
