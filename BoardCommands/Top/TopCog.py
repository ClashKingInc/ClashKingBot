from disnake.ext import commands
from .TopButtons import TopButtons
from .TopCommands import TopCommands

class TopCog(TopCommands, TopButtons, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(TopCog(bot))