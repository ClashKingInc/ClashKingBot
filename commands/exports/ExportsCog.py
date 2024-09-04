from disnake.ext import commands

from .ExportCreator import ExportCreator
from .Exports import ExportCommands


class ExportCog(ExportCommands, ExportCreator, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot


def setup(bot):
    bot.add_cog(ExportCog(bot))
