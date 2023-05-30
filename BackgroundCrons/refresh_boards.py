from disnake.ext import commands
import coc
import asyncio
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from utils.ClanCapital import get_raidlog_entry, gen_raid_weekend_datestrings
from pymongo import UpdateOne
from coc.raid import RaidLogEntry

class RefreshBoards(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.refresh, 'interval', minutes=10)

    async def refresh(self):
        pass







def setup(bot: CustomClient):
    bot.add_cog(RefreshBoards(bot))