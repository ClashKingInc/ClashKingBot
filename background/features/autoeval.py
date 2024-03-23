from disnake.ext import commands
import coc
import disnake
import math

from typing import TYPE_CHECKING
from classes.bot import CustomClient
from pymongo import InsertOne

class AutoEvalBackground(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.autoeval_update, "interval", minutes=60)

    async def autoeval_update(self):
        pass
        #go thru clans with achievement roles set up & update roles as such







def setup(bot: CustomClient):
    bot.add_cog(AutoEvalBackground(bot))