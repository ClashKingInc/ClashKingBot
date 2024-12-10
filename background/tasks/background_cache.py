from disnake.ext import commands, tasks

from classes.bot import CustomClient


class BackgroundCache(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.guilds_store.start()

    @tasks.loop(seconds=60)
    async def guilds_store(self):
        guild_id_list = set()
        total_members = 0
        server_names = []
        for guild in self.bot.guilds:
            guild_id_list.add(guild.id)
            total_members += guild.member_count
            server_names.append(f"{guild.name} | {guild.id}")

        self.bot.OUR_GUILDS = guild_id_list
        clan_tags = await self.bot.clan_db.distinct('tag', filter={'server': {'$in': list(guild_id_list)}})
        self.bot.OUR_CLANS = set(clan_tags)

        await self.bot.bot_sync.update_one({"$and" : [{"type" : "server_counts", "bot_id" : self.bot.user.id, "cluster_id" : self.bot._config.cluster_id}]},
                                           {"$set" : {"server_count" : len(guild_id_list), "member_count" : total_members,
                                                      "shards" : self.bot.shard_ids, "clan_count" : len(clan_tags)}}, upsert=True)

        await self.bot.bot_sync.update_one(
            {"$and": [{"type": "servers", "bot_id": self.bot.user.id, "cluster_id": self.bot._config.cluster_id}]},
            {"$set": {"names" : server_names}}, upsert=True)

    @guilds_store.before_loop
    async def before_guilds_store(self):
        await self.bot.wait_until_ready()


def setup(bot: CustomClient):

    bot.add_cog(BackgroundCache(bot))
