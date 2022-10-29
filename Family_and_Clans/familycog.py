from disnake.ext import commands
from Family_and_Clans.utils.family import getFamily
from .family_commands import family_commands

class clancog(getFamily, family_commands, commands.Cog, name="Family Commands"):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(clancog(bot))