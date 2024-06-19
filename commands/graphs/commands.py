from disnake.ext import commands
import disnake
from typing import TYPE_CHECKING
from classes.bot import CustomClient
from typing import List
from discord import autocomplete, convert, options

from .utils import daily_graph, monthly_bar_graph, season_line_graph
from utility.clash.other import gen_season_date
from exceptions.CustomExceptions import MessageException


class GraphCreator(commands.Cog, name="Graph Commands"):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="graph")
    async def graph(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @graph.sub_command(
        name="over-time", description="Details for a clan(s)/family over time"
    )
    async def graph_over_time(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        attribute: str = commands.Param(
            choices=[
                "Activity",
                "Clan Games",
                "Attack Wins",
                "Donations",
                "Received",
                "CWL Leagues",
                "Capital Leagues",
                "Capital Trophies",
            ]
        ),
        months: int = 4,
        limit: int = commands.Param(default=15, min_value=1, max_value=50),
        family: disnake.Guild = options.optional_family,
        clans: List[str] = commands.Param(
            default=None,
            converter=convert.multi_clan,
            autocomplete=autocomplete.multi_clan,
        ),
    ):
        family = family or ctx.guild
        if clans is None:
            clans = await self.bot.clan_db.distinct("tag", filter={"server": family.id})
        else:
            clans = [clan.split("|")[-1] if "|" in clan else clan for clan in clans]
        graph, web = await season_line_graph(
            clan_tags=clans,
            months=months,
            bot=self.bot,
            attribute=attribute.lower().replace(" ", "_"),
            limit=limit,
            html=True,
        )
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                style=disnake.ButtonStyle.url, label="Online View", url=web
            )
        )
        await ctx.send(file=graph, components=[buttons])

    @graph.sub_command(
        name="month", description="Bar Chart comparing clans for an attribute"
    )
    async def graph_over_month(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        attribute: str = commands.Param(
            choices=[
                "Gold Looted",
                "Elixir Looted",
                "DE Looted",
                "Donations",
                "Received",
                "Attack Wins",
                "Activity",
                "Capital Gold Donated",
                "Capital Gold Raided",
                "Average Raid Participants",
                "Troops Upgraded",
                "Heroes Upgraded",
                "War Stars",
                "Wars Won",
                "Wars Spun",
            ]
        ),  # 15 room for 10 more
        season: str = options.optional_season,
        server: disnake.Guild = options.optional_family,
    ):
        season = season or gen_season_date()
        server = server or ctx.guild
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": server.id})
        if len(clan_tags) <= 1:
            raise MessageException("Cannot run command with less than 2 clans")
        graph, web = await monthly_bar_graph(
            bot=self.bot,
            clan_tags=clan_tags,
            attribute=attribute.lower().replace(" ", "_"),
            season=season,
            html=True,
        )
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                style=disnake.ButtonStyle.url, label="Online View", url=web
            )
        )
        await ctx.send(file=graph, components=[buttons])

    @graph.sub_command(
        name="daily", description="Line chart showing attribute over time"
    )
    async def graph_daily(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        attribute: str = commands.Param(
            choices=[
                "activity",
                "troop upgrades",
                "hero upgrades",
                "hero equipment",
                "warStars",
                "bestTrophies",
                "townHallLevel",
                "townHallWeaponLevel",
                "role",
                "name",
                "league",
                "expLevel",
                "defenseWins",
                "clanCapitalContributions",
                "clan",
                "builderHallLevel",
                "warPreference",
            ]
        ),
        months: int = commands.Param(
            default=1,
            description="Months lookback (for activity this is how many seasons ago to view)",
        ),
        limit: int = commands.Param(default=15, min_value=1, max_value=50),
        clans: List[str] = commands.Param(
            default=None,
            converter=convert.multi_clan,
            autocomplete=autocomplete.multi_clan,
        ),
        family: disnake.Guild = commands.Param(
            converter=convert.server, default=None, autocomplete=autocomplete.server
        ),
    ):
        family = family or ctx.guild
        if clans is None:
            clans = await self.bot.clan_db.distinct("tag", filter={"server": family.id})
        else:
            clans = [clan.split("|")[-1] if "|" in clan else clan for clan in clans]
        graph, web = await daily_graph(
            bot=self.bot,
            clan_tags=clans,
            months=months,
            attribute=attribute.replace(" ", ""),
            limit=limit,
            html=True,
        )
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                style=disnake.ButtonStyle.url, label="Online View", url=web
            )
        )
        await ctx.send(file=graph, components=[buttons])


def setup(bot):
    bot.add_cog(GraphCreator(bot))
