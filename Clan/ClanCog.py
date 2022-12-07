from disnake.ext import commands
from Clan.ClanUtils import getClans
from .ClanCommands import clan_commands


class clancog(getClans, clan_commands, commands.Cog, name="Clan Commands"):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot


def setup(bot):
    bot.add_cog(clancog(bot))
