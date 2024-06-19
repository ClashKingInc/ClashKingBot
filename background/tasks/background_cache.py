from classes.bot import CustomClient
from disnake.ext import commands, tasks


class BackgroundCache(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.guilds_store.start()

    @tasks.loop(seconds=60)
    async def guilds_store(self):
        if not self.bot.user.public_flags.verified_bot and self.bot.user.id != 808566437199216691:
            guild_id_list = [guild.id for guild in self.bot.guilds]
            await self.bot.custom_bots.update_one(
                {"token": self.bot._config.bot_token},
                {"$set": {"server_ids": guild_id_list}},
            )
        else:
            guild_id_list = [guild.id for guild in self.bot.guilds]
            custom_bot_guilds = set(await self.bot.custom_bots.distinct("server_ids"))
            guild_id_list = [id for id in guild_id_list if id not in custom_bot_guilds]

        self.bot.OUR_GUILDS = set(guild_id_list)
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": {"$in": guild_id_list}})
        self.bot.OUR_CLANS = set(clan_tags)
        self.bot.CLANS_LOADED = True

    @guilds_store.before_loop
    async def before_guilds_store(self):
        await self.bot.wait_until_ready()


def setup(bot: CustomClient):

    bot.add_cog(BackgroundCache(bot))
