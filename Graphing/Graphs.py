from disnake.ext import commands
import disnake
from CustomClasses.CustomBot import CustomClient
import coc
import plotly.express as px
import plotly.io as pio
import io
import pandas as pd
import datetime as dt
import plotly.graph_objects as go

from collections import defaultdict, Counter
from typing import List, TYPE_CHECKING
from discord.autocomplete import Autocomplete as autocomplete
from discord.converters import Convert as convert
from .over_time_graph import capital_stats_monthly_graph

class GraphCreator(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot




    @commands.slash_command(name="graph")
    async def g(self, ctx: disnake.ApplicationCommandInteraction, attribute: str = commands.Param(choices=["Raided", "Donated", "Attacks", "Medals"]), months: int = 6,
                family: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server),
                clans: List[str] = commands.Param(default=None, converter=convert.multi_clan, autocomplete=autocomplete.multi_clan)):
        await ctx.response.defer()
        if family is None and clans is None:
            family = ctx.guild
        if family is not None and clans is None:
            clans = await self.bot.clan_db.distinct("tag", filter={"server": family.id})
        graph = await capital_stats_monthly_graph(clan_tags=clans, months=months, bot=self.bot, attribute=attribute.lower())
        await ctx.send(file=graph)




def setup(bot):
    bot.add_cog(GraphCreator(bot))
