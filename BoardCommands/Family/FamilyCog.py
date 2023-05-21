from disnake.ext import commands
from .FamilyCommands import FamCommands
from .FamilyEmbeds import FamilyUtils
from .FamilyButtons import FamilyButtons

class FamilyCog(FamCommands, FamilyUtils, FamilyButtons, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(FamilyCog(bot))