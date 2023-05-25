from disnake.ext import commands
from .ClanCommands import ClanCommands
from .ClanButtons import ClanButtons
from .ClanEmbeds import ClanEmbedGenerator

class ClanCog(ClanCommands, ClanButtons, ClanEmbedGenerator, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(ClanCog(bot))