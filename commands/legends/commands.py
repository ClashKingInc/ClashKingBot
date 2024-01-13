import coc.utils
import disnake
from disnake.ext import commands

from CustomClasses.CustomBot import CustomClient
from utility.constants import POSTER_LIST
from discord.autocomplete import Autocomplete as autocomplete
from discord.converters import Convert as convert
from exceptions.CustomExceptions import MessageException, PlayerNotInLegends
from .utils import legend_day_overview, legend_clan, legend_history, legend_poster
from CustomClasses.DatabaseClient.Classes.player import LegendPlayer
from typing import List

from .buttons import LegendButtons


class Legends(LegendButtons, commands.Cog):
    def __init__(self, bot: CustomClient):
        super().__init__(bot)
        self.bot = bot

    @commands.slash_command(name="check")
    async def check(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @check.sub_command(name="search", description="Outdated legends command")
    async def check_search(self, ctx: disnake.ApplicationCommandInteraction,
                           player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player)):
        await ctx.send("This command has been renamed to `/legends search` and will be removed in the next 30 days.")


    @commands.slash_command(name="legends")
    async def legends(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user": ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)


    @legends.sub_command(name="search", description="View legend stats for a player or discord user")
    async def legends_search(self, ctx: disnake.ApplicationCommandInteraction,
                           player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player)):
        """
            Parameters
            ----------
            player: player to get legends info on
        """

        if player.league.name != "Legend League":
            raise PlayerNotInLegends

        #make sure player has unpaused tracking
        await self.bot.player_stats.update_one({"tag": player.tag}, {"$set": {"paused": False}})
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        legend_player = await self.bot.ck_client.get_legend_player(player=player)
        embed = await legend_day_overview(bot=self.bot, player=legend_player, embed_color=embed_color)
        buttons = [
            disnake.ui.Button(label=f"Today", style=disnake.ButtonStyle.grey, custom_id=f"legendday_{player.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.calendar.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"legendseason_{player.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.clock.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"legendhistory_{player.tag}"),
            disnake.ui.Button(label="➕", style=disnake.ButtonStyle.grey, custom_id=f"legendquick_{player.tag}"),
        ]
        await ctx.send(embed=embed, components=buttons)


    @legends.sub_command(name="clan", description="View a clan's legend day results")
    async def legends_clan(self, ctx: disnake.ApplicationCommandInteraction,
                           clan: coc.Clan = commands.Param(autocomplete=autocomplete.clan, converter=convert.clan)):
        """
            Parameters
            ----------
            clan: Search for a clan by name or tag
        """
        legend_players: List[LegendPlayer] = await self.bot.ck_client.get_clan_legend_players(clan=clan)
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await legend_clan(players=legend_players, clan=clan, embed_color=embed_color)
        await ctx.send(embed=embed)


    @legends.sub_command(name="history", description="View legend history of an account")
    async def legend_history(self, ctx: disnake.ApplicationCommandInteraction,
                             player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player)):

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        legend_player = await self.bot.ck_client.get_legend_player(player=player)
        embed = await legend_history(bot=self.bot, player=legend_player, embed_color=embed_color)
        await ctx.send(embed=embed)


    @legends.sub_command(name="poster", description="Poster w/ graph & stats to show off season legends stats")
    async def legend_poster(self, ctx: disnake.ApplicationCommandInteraction,
                            player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player),
                            background: str = commands.Param(default=None,choices=list(POSTER_LIST.keys()))):
        """
            Parameters
            ----------
            smart_search: Name or player tag to search with
            background: Which background for poster to use (optional)
        """
        legend_player = await self.bot.ck_client.get_legend_player(player=player)
        poster_link: str = await legend_poster(player=legend_player, background=background)
        await ctx.send(content=poster_link)



def setup(bot):
    bot.add_cog(Legends(bot))
