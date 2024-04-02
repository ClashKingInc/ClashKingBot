import disnake
import coc
import calendar

from disnake.ext import commands
from typing import TYPE_CHECKING
from classes.bot import CustomClient
from utility.constants import item_to_name
from utility.ClanCapital import gen_raid_weekend_datestrings

from BoardCommands.Utils import Shared as shared_embeds


class TopCommands(commands.Cog, name="Top"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

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
        await ctx.response.defer()


    @top.sub_command(name="donations", description="Top donators across the bot")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction, season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        players = await self.bot.player_stats.find({}, {"tag" : 1}).sort(f"donations.{season}.donated", -1).limit(50).to_list(length=50)
        players = await self.bot.get_players(tags=[result.get("tag") for result in players])

        footer_icon = self.bot.user.avatar.url
        embed: disnake.Embed = await shared_embeds.donation_board(bot=self.bot, players=players, season=season, footer_icon=footer_icon, title_name="ClashKing", type="donations")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topdonatedplayer_"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topreceivedplayer_"))
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @top.sub_command(name="compo", description="Composition of a family. (with a twist?)")
    async def family_compo(self, ctx: disnake.ApplicationCommandInteraction,
                           type: str = commands.Param(default="Totals", choices=["Totals", "Hitrate"])):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            type: type of compo calculation
        """

        member_tags = []

        if type == "Totals":
            embed = await shared_embeds.th_composition(bot=self.bot,
                                                       player_tags=member_tags,
                                                       title=f"Bot Townhall Composition", thumbnail=self.bot.user.avatar.url)
        elif type == "Hitrate":
            embed = await shared_embeds.th_hitrate(bot=self.bot,
                                                   player_tags=member_tags,
                                                   title=f"Bot TH Hitrate Compo", thumbnail=self.bot.user.avatar.url)


        await ctx.edit_original_message(embed=embed, components=None)


    @top.sub_command(name="activities", description="Members with the highest activity on the bot")
    async def activities(self, ctx: disnake.ApplicationCommandInteraction, season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        pipeline = [
            {"$project": {"tag": "$tag", "activity_len": {"$size": {"$ifNull": [f"$last_online_times.{season}", []]}}}},
            {"$sort": {"activity_len": -1}}, {"$limit": 50}]
        players = await self.bot.player_stats.aggregate(pipeline).to_list(length=None)
        players = await self.bot.get_players(tags=[result.get("tag") for result in players])

        footer_icon = self.bot.user.avatar.url
        embed: disnake.Embed = await shared_embeds.activity_board(bot=self.bot, players=players, season=season,
                                                                   footer_icon=footer_icon, title_name="ClashKing")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topactivityplayer_{season}"))
        await ctx.edit_original_message(embed=embed, components=[])


    @top.sub_command(name="sorted", description="Top players by attribute")
    async def sorted(self, ctx: disnake.ApplicationCommandInteraction,
                     sort_by: str = commands.Param(choices=sorted(item_to_name.keys())),
                     limit: int = commands.Param(default=50, min_value=1, max_value=50)):

        embed = await shared_embeds.player_sort(bot=self.bot, player_tags=[],
                                                sort_by=sort_by,
                                                footer_icon=self.bot.user.avatar.url,
                                                title_name=f"All Players sorted by {sort_by}", limit=limit)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"topsort_{sort_by}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])


    @top.sub_command(name="capital", description="Top capital contributors across the bot")
    async def capital(self, ctx: disnake.ApplicationCommandInteraction, weekend: str = None):
        if weekend is None:
            week = self.bot.gen_raid_date()
        else:
            week = weekend
        pipeline = [{"$project" : {"tag" : "$tag", "capital_sum" : {"$sum" : { "$ifNull": [f"$capital_gold.{week}.donate", [] ]}}}}, {"$sort":{"capital_sum":-1}}, {"$limit" : 50}]
        players = await self.bot.player_stats.aggregate(pipeline).to_list(length=None)
        players = await self.bot.get_players(tags=[result.get("tag") for result in players])
        embed: disnake.Embed = await shared_embeds.capital_donation_board(bot=self.bot, players=players, week=week, title_name="Top", footer_icon=self.bot.user.avatar.url)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="Donated", emoji=self.bot.emoji.capital_gold.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topcapitaldonatedplayer_{weekend}"))
        buttons.append_item(disnake.ui.Button(
            label="Raided", emoji=self.bot.emoji.thick_sword.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"topcapitalraidplayer_{weekend}"))
        await ctx.send(embed=embed, components=[buttons])


    @donations.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    @capital.autocomplete("weekend")
    async def weekend(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        weekends = gen_raid_weekend_datestrings(number_of_weeks=25)
        matches = []
        for weekend in weekends:
            if query.lower() in weekend.lower():
                matches.append(weekend)
        return matches


def setup(bot):
    bot.add_cog(TopCommands(bot))
