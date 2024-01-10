from disnake.ext import commands
import coc
import disnake
import math
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from pymongo import InsertOne

class AutoEvalBackground(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.autoeval_update, "interval", minutes=60)

    async def autoeval_update(self):
        pass
        #go thru clans with achievement roles set up & update roles as such







def setup(bot: CustomClient):
    bot.add_cog(AutoEvalBackground(bot))