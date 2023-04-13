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
    from TopCog import TopCog
    board_cog = BoardCog
    top_cog = TopCog
else:
    board_cog = commands.Cog
    top_cog = commands.Cog

class TopCommands(top_cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.board_cog: BoardCog = bot.get_cog("BoardCog")


    async def season_convertor(self, season: str):
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            season_date = f"{end_date.year}-{month}"
        else:
            season_date = self.bot.gen_season_date()
        return season_date

    @commands.slash_command(name="top")
    async def top(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user": ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)


    @top.sub_command(name="donations", description="Top donators across the entire bot")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction, season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        players = await self.bot.player_stats.find({}, {"tag" : 1}).sort(f"donations.{season}.donated", -1).limit(50).to_list(length=50)
        players = await self.bot.get_players(tags=[result.get("tag") for result in players])

        footer_icon = self.bot.user.avatar.url
        embed: disnake.Embed = await self.board_cog.donation_board(players=players, season=season, footer_icon=footer_icon, title_name="ClashKing", type="donations")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topdonatedplayer_"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topreceivedplayer_"))
        buttons.append_item(disnake.ui.Button(
            label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topratioplayer_"))
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @donations.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]
