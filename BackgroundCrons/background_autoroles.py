from disnake.ext import commands
import coc
import disnake
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from pymongo import InsertOne

class EvalLoop(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.autoboard_cron, "cron", hour=4, minute=57)





def setup(bot: CustomClient):
    bot.add_cog(EvalLoop(bot))