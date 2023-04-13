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
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
else:
    cog_class = commands.Cog

from utils.constants import item_to_name
from disnake.ext.commands import Converter


class ClanCommands(commands.Cog, name="Clan Commands"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan: str):
        clan = await self.bot.getClan(clan_tag=clan, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan


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


    @commands.slash_command(name="clan")
    async def clan(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user" : ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)


    @clan.sub_command(name="donations", description="Donations given & received by clan members")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                             season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):

        players = await self.bot.get_players(tags=[member.tag for member in clan.members])

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        embed: disnake.Embed = await board_cog.donation_board(players=players, season=season, footer_icon=clan.badge.url, title_name=f"{clan.name}", type="donations")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"donated_{season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"received_{season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"ratio_{season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="activity", description="Activity stats for all of a player's accounts")
    async def activity(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                       season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):

        players = await self.bot.get_players(tags=[member.tag for member in clan.members])

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        footer_icon = clan.badge.url
        embed: disnake.Embed = await board_cog.activity_board(players=players, season=season, footer_icon=footer_icon, title_name=f"{clan.name}")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"act_{season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Last Online", emoji=self.bot.emoji.clock.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"lo_{season}_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(
            label="Graph", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"actgraphclan_{season}_{clan.tag}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])

    @clan.sub_command(name="activity-graph")
    async def activity_graph(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                       season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                       granularity: str = commands.Param(default="Day", choices=["Hour", "Quarter-Day", "Day"]),
                       timezone: str = "UTC"):

        players = await self.bot.get_players(tags=[member.tag for member in clan.members])

        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        members = []
        clans = await self.bot.get_clans(tags=clan_tags)
        for clan in clans:
            members += [member.tag for member in clan.members]

        players = await self.bot.get_players(tags=members)

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        file, buttons = await board_cog.activity_graph(players=players, season=season, title=f"{clan.name} Activity ({season})", granularity=granularity, time_zone=timezone)
        await ctx.send(file=file, components=[buttons])


    @donations.autocomplete("season")
    @activity.autocomplete("season")
    @activity_graph.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    @donations.autocomplete("clan")
    @activity.autocomplete("clan")
    @activity_graph.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id}).sort("name", 1)
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=5)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]

    @activity_graph.autocomplete("timezone")
    async def timezone_autocomplete(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
        return return_list[:25]

