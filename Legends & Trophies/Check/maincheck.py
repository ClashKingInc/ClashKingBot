from disnake.ext import commands
from .check import Check
from .check_stats import CheckStats
from .history import History
from .pagination import Pagination
from .quick_check import QuickCheck


class Legends(Check, CheckStats, History, Pagination, QuickCheck, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(Legends(bot))