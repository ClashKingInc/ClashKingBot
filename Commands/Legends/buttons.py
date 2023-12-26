import coc.utils
import contextlib
import disnake
from disnake.ext import commands
import emoji
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from Utils.components import create_components
from Discord.autocomplete import Autocomplete as autocomplete
from Discord.converters import Convert as convert
from Exceptions.CustomExceptions import NoLinkedAccounts, PlayerNotInLegends
from .utils import legend_day_overview, legend_season_overview, legend_history
from CustomClasses.DatabaseClient.Classes.player import LegendPlayer
from typing import List
import uuid


class LegendButtons(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if ctx.data.custom_id.startswith("legend"):
            await ctx.response.defer()
            '''buttons = [
            disnake.ui.Button(label=f"Today", style=disnake.ButtonStyle.grey, custom_id=f"legendday_{player.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.calendar.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"legendseason_{player.tag}"),
            disnake.ui.Button(label="", emoji=self.bot.emoji.clock.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"legendhistory_{player.tag}"),
            disnake.ui.Button(label="➕", style=disnake.ButtonStyle.grey, custom_id=f"legendquick_{player.tag}"),
            ]'''
            type, tag = ctx.data.custom_id.split("_")
            embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
            player = await self.bot.getPlayer(player_tag=tag)
            legend_player = await self.bot.ck_client.get_legend_player(player=player)
            embed = None
            if type == "legendday":
                embed = await legend_day_overview(bot=self.bot, player=legend_player, embed_color=embed_color)
            elif type == "legendseason":
                embed = await legend_season_overview(player=legend_player, embed_color=embed_color)
            elif type == "legendhistory":
                embed = await legend_history(bot=self.bot, player=legend_player, embed_color=embed_color)
            elif type == "legendquick":
                results = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
                profile_tags = results.get("profile_tags", [])
                if tag in profile_tags:
                    await self.bot.legend_profile.update_one({'discord_id': ctx.author.id}, {'$pull': {"profile_tags": tag, "feed_tags": tag}})
                    await ctx.send(content=f"Removed {player.name} from your Quick Check & Daily Report list.", ephemeral=True)
                elif len(profile_tags) >= 25:
                    await ctx.send(content="Can only have 25 players on your Quick Check & Daily Report list. Please remove one.", ephemeral=True)
                else:
                    await self.bot.legend_profile.update_one({'discord_id': ctx.author.id}, {'$push': {"profile_tags": tag}}, upsert=True)
                    await ctx.send(content=f"Added {player.name} to your Quick Check & Daily Report list.", ephemeral=True)

            if embed:
                await ctx.edit_original_message(embed=embed)


