import disnake
import calendar
import coc

from disnake.ext import commands
from typing import List
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import *
from DiscordLevelingCard import RankCard, Settings
from operator import attrgetter
from datetime import date, timedelta, datetime

from utils.discord_utils import interaction_handler
from utils.player_pagination import button_pagination
from utils.components import player_components
from utils.search import search_results
from utils.constants import LEVELS_AND_XP

from BoardCommands.Utils import Shared as shared_embeds
from BoardCommands.Utils import Player as player_embeds

from Discord.converters import Convert as convert
from Discord.autocomplete import Autocomplete as autocomplete


class Donations(commands.Cog, name="Donations"):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="donations")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction,
                        player: List[coc.Player] = commands.Param(default=None, converter=convert.player, autocomplete=autocomplete.family_players),
                        user: disnake.Member = None,
                        clan: coc.Clan = commands.Param(default=None, converter=convert.clan, autocomplete=autocomplete.clan),
                        family: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server),
                        limit: int = commands.Param(default=50, max_value=50),
                        townhalls: List[int] = commands.Param(default=None, convert_defaults=True, converter=convert.townhall),
                        season: str = commands.Param(default=None, convert_defaults=True, converter=convert.season, autocomplete=autocomplete.season)):
        print(season)
        await ctx.send(townhalls)








def setup(bot: CustomClient):
    bot.add_cog(Donations(bot))
