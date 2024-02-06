import coc.utils
import disnake
from disnake.ext import commands

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake.ext.commands import AutoShardedBot as CustomClient
from utility.constants import POSTER_LIST
from discord import autocomplete, convert, options
from exceptions.CustomExceptions import PlayerNotInLegends
from .utils import legend_day_overview, legend_clan, legend_history, legend_poster, legend_cutoff, legend_streaks, legend_buckets, legend_eos_finishers


class Legends(commands.Cog):
    def __init__(self, bot: CustomClient):
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
        embed = await legend_day_overview(bot=self.bot, player=player, embed_color=embed_color)
        buttons = [
            disnake.ui.Button(label=f"Today", style=disnake.ButtonStyle.grey, custom_id=f"legendday:{player.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.calendar.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"legendseason:{player.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.clock.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"legendhistory:{player.tag}"),
            disnake.ui.Button(label="➕", style=disnake.ButtonStyle.grey, custom_id=f"legendquick:ctx:{player.tag}"),
        ]
        await ctx.send(embed=embed, components=buttons)


    @legends.sub_command(name="clan", description="View a clan's legend day results")
    async def legends_clan(self, ctx: disnake.ApplicationCommandInteraction,
                           clan: coc.Clan = options.clan):
        """
            Parameters
            ----------
            clan: Search for a clan by name or tag
        """
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await legend_clan(bot=self.bot, clan=clan, embed_color=embed_color)
        await ctx.send(embed=embed)


    @legends.sub_command(name="history", description="View legend history of an account")
    async def legend_history(self, ctx: disnake.ApplicationCommandInteraction,
                             player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player)):
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await legend_history(bot=self.bot, player=player, embed_color=embed_color)
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
        poster_link: str = await legend_poster(bot=self.bot, player=player, background=background)
        await ctx.send(content=poster_link)


    @legends.sub_command(name="stats", description="View various legend related stats")
    async def legend_stats(self, ctx: disnake.ApplicationCommandInteraction,
                            type: str = commands.Param(choices=["Rank Cutoff", "Triple Streaks", "Trophy Buckets", "EOS Finishers"]),
                            limit: int = commands.Param(default=50, min_value=1, max_value=50)):
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        if type == "Rank Cutoff":
            embed = await legend_cutoff(bot=self.bot, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"legendcutoff:"))
        elif type == "Triple Streaks":
            embed = await legend_streaks(bot=self.bot, limit=limit, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"legendstreaks:{limit}"))
        elif type == "Trophy Buckets":
            embed = await legend_buckets(bot=self.bot, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"legendbuckets:"))
        elif type == "EOS Finishers":
            embed = await legend_eos_finishers(bot=self.bot, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f"legendeosfinishers:"))
        await ctx.edit_original_message(embed=embed, components=[buttons])



def setup(bot):
    bot.add_cog(Legends(bot))
