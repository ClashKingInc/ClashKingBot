from disnake.ext import commands
#from .Setup import SetupCommands
from .SetupUtils import SetupUtils

class SetupCog(SetupUtils, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot


def setup(bot):
    bot.add_cog(SetupCog(bot))
