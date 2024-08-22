import disnake
from disnake.ext import commands

from classes.bot import CustomClient


class EmbedShare(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.channel.id == 1227792195205992458:
            pass


def setup(bot: CustomClient):
    bot.add_cog(EmbedShare(bot))
