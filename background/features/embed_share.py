import disnake
import re

from classes.bot import CustomClient
from commands.clan.utils import basic_clan_board
from commands.utility.utils import army_embed
from commands.player.utils import basic_player_board
from disnake.ext import commands
from urllib.parse import urlparse, parse_qs
from utility.cdn import upload_to_cdn
from utility.general import safe_run

class EmbedShare(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.channel.id == 1227792195205992458:







def setup(bot: CustomClient):
    bot.add_cog(EmbedShare(bot))