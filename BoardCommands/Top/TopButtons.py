
import pytz
import disnake

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
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

class TopButtons(top_cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.board_cog: board_cog = bot.get_cog("BoardCog")

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):

        if str(ctx.data.custom_id) == "topdonatedplayer_":
            await ctx.response.defer()
            season = self.bot.gen_season_date()
            players = await self.bot.player_stats.find({}, {"tag": 1}).sort(f"donations.{season}.donated", -1).limit(50).to_list(length=50)
            players = await self.bot.get_players(tags=[result.get("tag") for result in players])

            footer_icon = self.bot.user.avatar.url
            embed: disnake.Embed = await self.board_cog.donation_board(players=players, season=season,
                                                                       footer_icon=footer_icon, title_name="ClashKing",
                                                                       type="donations")
            await ctx.edit_original_message(embed=embed)

        elif str(ctx.data.custom_id) == "topreceivedplayer_":
            await ctx.response.defer()
            season = self.bot.gen_season_date()
            players = await self.bot.player_stats.find({}, {"tag": 1}).sort(f"donations.{season}.received", -1).limit(50).to_list(length=50)
            players = await self.bot.get_players(tags=[result.get("tag") for result in players])

            footer_icon = self.bot.user.avatar.url
            embed: disnake.Embed = await self.board_cog.donation_board(players=players, season=season,
                                                                       footer_icon=footer_icon, title_name="ClashKing",
                                                                       type="received")
            await ctx.edit_original_message(embed=embed)

        elif "topcapitaldonatedplayer_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            week = str(ctx.data.custom_id).split("_")[-1]
            if week == "None":
                week = self.bot.gen_raid_date()
            pipeline = [{"$project": {"tag": "$tag",
                                      "capital_sum": {"$sum": {"$ifNull": [f"$capital_gold.{week}.donate", []]}}}},
                        {"$sort": {"capital_sum": -1}}, {"$limit": 50}]
            players = await self.bot.player_stats.aggregate(pipeline).to_list(length=None)
            players = await self.bot.get_players(tags=[result.get("tag") for result in players])
            embed: disnake.Embed = await self.board_cog.capital_donation_board(players=players, week=week,
                                                                               title_name="Top",
                                                                               footer_icon=self.bot.user.avatar.url)
            await ctx.edit_original_message(embed=embed)

        elif "topcapitalraidplayer_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            week = str(ctx.data.custom_id).split("_")[-1]
            if week == "None":
                week = self.bot.gen_raid_date()
            pipeline = [{"$project": {"tag": "$tag",
                                      "capital_sum": {"$sum": {"$ifNull": [f"$capital_gold.{week}.raid", []]}}}},
                        {"$sort": {"capital_sum": -1}}, {"$limit": 50}]
            players = await self.bot.player_stats.aggregate(pipeline).to_list(length=None)
            players = await self.bot.get_players(tags=[result.get("tag") for result in players])
            embed: disnake.Embed = await self.board_cog.capital_raided_board(players=players, week=week,
                                                                               title_name="Top",
                                                                               footer_icon=self.bot.user.avatar.url)
            await ctx.edit_original_message(embed=embed)



