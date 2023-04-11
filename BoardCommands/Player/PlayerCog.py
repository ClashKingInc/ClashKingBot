from disnake.ext import commands
from .PlayerCommands import PlayerCommands


class PlayerCog(PlayerCommands, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(PlayerCog(bot))