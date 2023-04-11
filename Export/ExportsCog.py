from disnake.ext import commands
from .PlayerExports import PlayerExportCreator
from .Exports import ExportCommands

class ExportCog(ExportCommands, PlayerExportCreator, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(ExportCog(bot))