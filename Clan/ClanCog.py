from disnake.ext import commands
from Clan import (
    ClanCommands,
    ClanUtils
)


class ClanCog(
        ClanCommands.ClanCommands, ClanUtils.ClanUtils,
        commands.Cog, name="Clan Commands"):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot


def setup(bot):
    bot.add_cog(ClanCog(bot))
