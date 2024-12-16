from disnake.ext import commands, tasks

from classes.bot import CustomClient, ShardData


class BackgroundCache(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.guilds_store.start()

    @tasks.loop(seconds=60)
    async def guilds_store(self):
        guild_id_list = set()
        total_members = 0
        servers = []
        for guild in self.bot.guilds:
            guild_id_list.add(guild.id)
            total_members += guild.member_count
            servers.append({"id": guild.id, "name": guild.name, "members": guild.member_count})

        self.bot.OUR_GUILDS = guild_id_list
        clan_tags = await self.bot.clan_db.distinct('tag', filter={'server': {'$in': list(guild_id_list)}})
        self.bot.OUR_CLANS = set(clan_tags)

        await self.bot.bot_sync.update_one({"$and" : [{"type" : "server_counts", "bot_id" : self.bot.user.id, "cluster_id" : self.bot._config.cluster_id}]},
                                           {"$set" : {"server_count" : len(guild_id_list), "member_count" : total_members,
                                                      "shards" : self.bot.shard_ids, "clan_count" : len(clan_tags), "servers" : servers}}, upsert=True)

        shard_data = await self.bot.bot_sync.find({"bot_id" : self.bot.user.id}).to_list(length=None)
        self.bot.SHARD_DATA = [ShardData(data=d) for d in shard_data]

        self.bot.SERVER_MAP = {g.id : g for shard in self.bot.SHARD_DATA for g in shard.servers}

        channel = self.bot.get_channel(937528942661877851)
        if channel is not None:
            number_of_servers = len(list(self.bot.SERVER_MAP.keys()))
            new_channel_name = f'ClashKing: {number_of_servers} Servers'
            if new_channel_name != channel.name:
                await channel.edit(name=new_channel_name)


    @guilds_store.before_loop
    async def before_guilds_store(self):
        await self.bot.wait_until_ready()


def setup(bot: CustomClient):

    bot.add_cog(BackgroundCache(bot))
