import math
from typing import TYPE_CHECKING

import coc
import disnake
from disnake.ext import commands
from pymongo import InsertOne

from classes.bot import CustomClient


class AutoEvalBackground(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.status_roles, 'interval', minutes=60)

    async def status_roles(self):
        pass


def setup(bot: CustomClient):
    bot.add_cog(AutoEvalBackground(bot))
