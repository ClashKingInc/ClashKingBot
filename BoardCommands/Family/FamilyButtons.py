import disnake
import coc
import pytz
import operator
import json
import asyncio
import calendar

from disnake.ext import commands
from coc import utils
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from collections import defaultdict
from collections import Counter
from datetime import datetime
from CustomClasses.Enums import TrophySort
from utils.constants import item_to_name

from typing import TYPE_CHECKING

tiz = pytz.utc
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    from FamilyCog import FamilyCog
    board_cog = BoardCog
    family_cog = FamilyCog
else:
    board_cog = commands.Cog
    family_cog = commands.Cog

class FamilyButtons(family_cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "donationfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="donated")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "receivedfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="received")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "ratiofam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_donations(ctx.guild, type="ratio")
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "lastonlinefam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_last_online(ctx.guild)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "activitiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed: disnake.Embed = await self.create_activities(ctx.guild)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

        elif "summaryfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            time = datetime.now()
            embeds = await self.create_summary(guild=ctx.guild, season=self.bot.gen_season_date())
            embeds[-1].timestamp = time
            embeds[-1].set_footer(text="Last Refreshed:")
            await ctx.edit_original_message(embeds=embeds)

        elif "cwlleaguesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_leagues(guild=ctx.guild, type="CWL")
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji,
                                  style=disnake.ButtonStyle.green,
                                  custom_id=f"cwlleaguesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.grey, custom_id=f"capitalleaguesfam_"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "capitalleaguesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_leagues(guild=ctx.guild, type="Capital")
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"cwlleaguesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green, custom_id=f"capitalleaguesfam_"))

            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "raidsfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_raids(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "clangamesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_clan_games(guild=ctx.guild)
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "joinhistoryfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_joinhistory(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "warsfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_wars(guild=ctx.guild)
            embed.set_footer(text="Last Refreshed:")
            embed.timestamp = datetime.now()
            await ctx.edit_original_message(embed=embed)

        elif "hometrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.home
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "versustrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.versus
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)

        elif "capitaltrophiesfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            sort_type = TrophySort.capital
            embed = await self.create_trophies(guild=ctx.guild, sort_type=sort_type)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,
                                                  custom_id=f"hometrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey,
                                                  custom_id=f"versustrophiesfam_"))
            buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                                  style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                                  custom_id=f"capitaltrophiesfam_"))
            await ctx.edit_original_message(embed=embed, components=buttons)