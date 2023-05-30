from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from utils.components import raid_buttons
from utils.discord_utils import partial_emoji_gen
from CustomClasses.CustomPlayer import MyCustomPlayer
from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from typing import TYPE_CHECKING, List
from coc import utils

import coc
import disnake
import pytz
import calendar

tiz = pytz.utc



class ClanButtons(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        board_cog = self.bot.get_cog("BoardCog")


        if "act_" in str(ctx.data.custom_id):
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            if len(str(ctx.data.custom_id).split("_")) == 3:
                season_date = (str(ctx.data.custom_id).split("_"))[-2]
            else:
                season_date = self.bot.gen_season_date()

            if len(str(ctx.data.custom_id).split("_")) == 4:
                await ctx.response.defer(ephemeral=True)
            else:
                await ctx.response.defer()

            players = await self.bot.get_players(tags=[member.tag for member in clan.members])
            embed = await board_cog.activity_board(players=players, season=season_date, footer_icon=clan.badge.url, title_name=f"{clan.name}")
            if len(str(ctx.data.custom_id).split("_")) == 4:
                await ctx.send(embed=embed, ephemeral=True)
            else:
                await ctx.edit_original_message(embed=embed)



