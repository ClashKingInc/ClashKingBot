from disnake.ext import commands
import disnake
from CustomClasses.CustomBot import CustomClient
from typing import List
from discord import autocomplete, convert

from .utils import monthly_capital_stats_graph, daily_graph
from utility.clash.other import gen_season_date
from exceptions.CustomExceptions import MessageException

class GraphCreator(commands.Cog, name="Graph Commands"):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="graph")
    async def graph(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @graph.sub_command(name="over-time", description="Details for a clan(s)/family over time")
    async def graph_over_time(self, ctx: disnake.ApplicationCommandInteraction,
                              attribute: str = commands.Param(choices=["Raided", "Donated", "Attacks", "Medals"]),
                              months: int = 6,
                              family: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server),
                              clans: List[str] = commands.Param(default=None, converter=convert.multi_clan, autocomplete=autocomplete.multi_clan)):
        if family is None and clans is None:
            family = ctx.guild
        if family is not None and clans is None:
            clans = await self.bot.clan_db.distinct("tag", filter={"server": family.id})
        graph = await monthly_capital_stats_graph(clan_tags=clans, months=months, bot=self.bot, attribute=attribute.lower())
        await ctx.send(file=graph)


    @graph.sub_command(name="month", description="Bar Chart comparing clans for an attribute")
    async def graph_over_month(self, ctx: disnake.ApplicationCommandInteraction,
                              attribute: str = commands.Param(choices=["Raided", "Donated", "Attacks", "Medals"]),
                              season: str = commands.Param(default=None, autocomplete=autocomplete.season),
                              family: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)):
        if season is None:
            season = gen_season_date()
        if family is None:
            family = ctx.guild
        clans = await self.bot.clan_db.distinct("tag", filter={"server": family.id})
        if len(clans) == 1:
            raise MessageException("Cannot run command with less than 2 clans")
        #graph = await monthly_capital_stats_graph(clan_tags=clans, months=months, bot=self.bot, attribute=attribute.lower())
        #await ctx.send(file=graph)



    @graph.sub_command(name="daily", description="Line chart showing attribute over time")
    async def graph_daily(self, ctx: disnake.ApplicationCommandInteraction,
                              attribute: str = commands.Param(choices=["activity", "troop upgrades", "hero upgrades", "hero equipment", "warStars",
                                                                       "bestTrophies", "townHallLevel", "townHallWeaponLevel", "role", "name",
                                                                       "league", "expLevel", "defenseWins", "clanCapitalContributions", "clan", "builderHallLevel", "warPreference"]),
                              months: int = commands.Param(default=1, description="Months lookback (for activity this is how many seasons ago to view)"),
                              clans: List[str] = commands.Param(default=None, converter=convert.multi_clan, autocomplete=autocomplete.multi_clan),
                              family: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)):
        if family is None:
            family = ctx.guild
        if clans is None:
            clans = await self.bot.clan_db.distinct("tag", filter={"server": family.id})
        clans = await self.bot.get_clans(tags=clans)
        graph, web = await daily_graph(bot=self.bot, clans=clans, months=months, attribute=attribute.replace(" ", ""), html=True)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(style=disnake.ButtonStyle.url, label="Online View", url=web))
        await ctx.send(file=graph, components=[buttons])




def setup(bot):
    bot.add_cog(GraphCreator(bot))
