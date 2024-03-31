from collections import deque
from classes.bot import CustomClient
from disnake.ext import commands, tasks
from utility.constants import BADGE_GUILDS

class EmojiRefresh(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.refresh.start()

    @tasks.loop(seconds=600)
    async def refresh(self):
        if self.bot.user.public_flags.verified_bot:
            emoji_map = {}
            for guild_id in BADGE_GUILDS:
                guild = await self.bot.getch_guild(guild_id)
                if guild is not None:
                    #only shard one needs to worry about deleting
                    if self.bot.shard_id == 1 and len(guild.emojis) >= 46 :
                        num_to_delete = len(guild.emojis) - 45
                        #sort from newest to oldest to remove the old ones
                        guild_emojis = sorted(guild.emojis, key=lambda x : x.id, reverse=True)
                        for emoji in guild_emojis[(-1 * num_to_delete):]:
                            await emoji.delete()

                    for emoji in guild.emojis:
                        emoji_map[emoji.name] = f"<:{emoji.name}:{emoji.id}>"
            self.bot.clan_badge_emoji_map = emoji_map
        else:
            our_badge_guild = [server.id for server in self.bot.guilds if server.owner_id == self.bot.user.id and server.name == "ckcustombotbadges"]
            if our_badge_guild:
                emoji_map = {}
                self.bot.BADGE_GUILDS = deque(our_badge_guild)
                for guild_id in self.bot.BADGE_GUILDS:
                    guild = await self.bot.getch_guild(guild_id)
                    #only shard one needs to worry about deleting
                    if self.bot.shard_id == 1 and len(guild.emojis) >= 46 :
                        num_to_delete = len(guild.emojis) - 45
                        #sort from newest to oldest to remove the old ones
                        guild_emojis = sorted(guild.emojis, key=lambda x : x.id, reverse=True)
                        for emoji in guild_emojis[(-1 * num_to_delete):]:
                            await emoji.delete()
                        for emoji in guild.emojis:
                            emoji_map[emoji.name] = f"<:{emoji.name}:{emoji.id}>"
                self.bot.clan_badge_emoji_map = emoji_map

    @refresh.before_loop
    async def before_refresh(self):
        await self.bot.wait_until_ready()


def setup(bot: CustomClient):
    bot.add_cog(EmojiRefresh(bot))
