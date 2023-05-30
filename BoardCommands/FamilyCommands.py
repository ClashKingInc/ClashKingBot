import datetime
import time

import disnake
import coc
import calendar

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import InvalidGuildID
from typing import TYPE_CHECKING, List
from utils.general import get_clan_member_tags
from utils.ClanCapital import gen_raid_weekend_datestrings
from pytz import utc


class FamCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def server_converter(self, server: str):
        try:
            guild = (await self.bot.getch_guild(int(server.split("|")[-1])))
        except:
            guild = None
        if guild is None:
            raise InvalidGuildID
        return guild

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

    async def th_convertor(self, th: str):
        if th is not None:
            return [int(th)]
        else:
            return list(range(2, 17))

    @commands.slash_command(name="family")
    async def family(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user": ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)
        self.board_cog: boardcog = self.bot.get_cog("BoardCog")
        self.graph_cog: graphcog = self.bot.get_cog("Graphing")

    @family.sub_command(name="clans", description="Overview list of all family clans")
    async def family_clans(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await self.create_family_clans(guild=guild)
        await ctx.edit_original_message(embed=embed)

    @family.sub_command(name="leagues", description="List of clans by cwl or capital league")
    async def family_leagues(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await self.create_leagues(guild=guild, type="CWL")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji,
                              style=disnake.ButtonStyle.green,
                              custom_id=f"cwlleaguesfam_"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.grey, custom_id=f"capitalleaguesfam_"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @family.sub_command(name="donations", description="Top 50 donators in family")
    async def family_donations(self, ctx: disnake.ApplicationCommandInteraction,
                               season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                               townhall: List[str] = commands.Param(default=None, convert_defaults=True, converter=th_convertor),
                               server: disnake.Guild = commands.Param(converter=server_converter, default=None),
                               limit: int = commands.Param(default=50, max_value=50)):

        guild = server if server is not None else ctx.guild
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)


        top_50 = await self.bot.player_stats.find({"$and" : [{"tag" :  {"$in": member_tags}}, {"townhall" : {"$in" : townhall}}]}, {"tag" : 1}).sort(f"donations.{season}.donated", -1).limit(limit).to_list(length=50)
        players = await self.bot.get_players(tags=[p["tag"] for p in top_50])
        graph, total_donos, total_received = await self.graph_cog.create_clan_donation_graph(clans=clans, season=season, type="donated", townhalls=townhall)
        embed = await self.board_cog.donation_board(players=players, season=season, title_name=f"{guild.name}", type="donations",
                                                    footer_icon=ctx.guild.icon.url if ctx.guild.icon is not None else self.bot.user.avatar.url,
                                                    total_donos=total_donos, total_received=total_received)
        embed.set_image(file=graph)

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,custom_id=f"donationfam_{season}_{limit}_{guild.id}_{None if len(townhall) >= 2 else townhall[0]}"))
        buttons.append_item(disnake.ui.Button(label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,style=disnake.ButtonStyle.grey, custom_id=f"receivedfam_{season}_{limit}_{guild.id}_{None if len(townhall) >= 2 else townhall[0]}"))
        buttons.append_item(disnake.ui.Button(label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"ratiofam_{season}_{limit}_{guild.id}_{None if len(townhall) >= 2 else townhall[0]}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @family.sub_command(name="capital", description="Top 50 capital contributors in family")
    async def family_capital(self, ctx: disnake.ApplicationCommandInteraction,
                             weekend: str = None,
                             townhall: List[str] = commands.Param(default=None, convert_defaults=True, converter=th_convertor),
                             server: disnake.Guild = commands.Param(converter=server_converter, default=None),
                             limit: int = commands.Param(default=50, max_value=50)):
        guild = server if server is not None else ctx.guild
        if weekend is None:
            week = self.bot.gen_raid_date()
        else:
            week = weekend
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)
        distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
        players = await self.bot.get_players(tags=distinct)
        embed: disnake.Embed = await self.board_cog.capital_donation_board(players=[player for player in players if player.town_hall in townhall], week=week,
                                                                           title_name=f"{guild.name} Top",
                                                                           footer_icon=guild.icon.url if guild.icon is not None else None, limit=limit)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="Donated", emoji=self.bot.emoji.capital_gold.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"famcapd_{weekend}_{limit}_{guild.id}_{None if len(townhall) >= 2 else townhall[0]}"))
        buttons.append_item(disnake.ui.Button(
            label="Raided", emoji=self.bot.emoji.thick_sword.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"famcapr_{weekend}_{limit}_{guild.id}_{None if len(townhall) >= 2 else townhall[0]}"))

        graph = await self.graph_cog.create_capital_graph(all_players=players, clans=clans, week=week, type="donations", server_id=guild.id)
        embed.set_image(url=f"{graph}?{int(datetime.datetime.now().timestamp())}")
        await ctx.send(embed=embed, components=[buttons])


    @family.sub_command(name="search", description="Overview Panel of a Family")
    async def family_search(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await self.create_search(guild=guild)
        await ctx.send(embed=embed)


    @family_clans.autocomplete("server")
    @family_leagues.autocomplete("server")
    @family_donations.autocomplete("server")
    @family_capital.autocomplete("server")
    @family_search.autocomplete("server")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        matches = []
        for guild in self.bot.guilds:
            if guild.member_count < 250:
                continue
            if query.lower() in guild.name.lower():
                matches.append(f"{guild.name} | {guild.id}")
            if len(matches) == 25:
                break
        return matches

    @family_donations.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

    @family_capital.autocomplete("weekend")
    async def weekend(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        weekends = gen_raid_weekend_datestrings(number_of_weeks=25)
        matches = []
        for weekend in weekends:
            if query.lower() in weekend.lower():
                matches.append(weekend)
        return matches


