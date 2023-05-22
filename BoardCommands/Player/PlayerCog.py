from disnake.ext import commands
from .PlayerCommands import PlayerCommands
from .PlayerButtons import PlayerButtons
from .PlayerEmbeds import PlayerEmbeds

class PlayerCog(PlayerCommands, PlayerButtons, PlayerEmbeds, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(PlayerCog(bot))