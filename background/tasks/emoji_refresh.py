import random

from classes.bot import CustomClient
from disnake.ext import commands, tasks
from utility.constants import BADGE_GUILDS

class EmojiRefresh(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.refresh.start()

    @tasks.loop(seconds=600)
    async def refresh(self):
        emoji_map = {}
        for guild_id in BADGE_GUILDS:
            guild = await self.bot.getch_guild(guild_id)
            if guild is not None:
                while len(guild.emojis) >= 46:
                    num_to_delete = random.randint(1, 5)
                    for emoji in guild.emojis[:num_to_delete]:
                        await guild.delete_emoji(emoji=emoji)
                for emoji in guild.emojis:
                    emoji_map[emoji.name] = f"<:{emoji.name}:{emoji.id}>"
        self.bot.clan_badge_emoji_map = emoji_map


def setup(bot: CustomClient):
    bot.add_cog(EmojiRefresh(bot))
