import re
from urllib.parse import parse_qs, urlparse

import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from commands.clan.utils import basic_clan_board
from commands.player.utils import basic_player_board
from commands.utility.utils import army_embed
from utility.cdn import upload_to_cdn
from utility.general import safe_run


class EmbedShare(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.channel.id == 1227792195205992458:
            pass


def setup(bot: CustomClient):
    bot.add_cog(EmbedShare(bot))
