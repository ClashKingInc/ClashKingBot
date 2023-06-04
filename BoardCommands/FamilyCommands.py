import datetime
import time

import disnake
import coc
import calendar

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import InvalidGuildID
from typing import List
from utils.general import get_clan_member_tags
from utils.ClanCapital import gen_raid_weekend_datestrings
from pytz import utc
from BoardCommands.Utils import Shared as shared_embeds
from BoardCommands.Utils import Graphs as graph_creator

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

    @commands.slash_command(name="countries")
    async def countries(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        await ctx.response.defer()
        guild = ctx.guild if server is None else server
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans = await self.bot.get_clans(tags=clan_tags)
        tags = []
        for clan in clans:
            for player in clan.members:
                tags.append(player.tag)

        pipeline = [
            {"$match": {"tag": {"$in": tags}}},
            {"$sort": {"country_name": 1}},
            {"$lookup": {"from": "player_stats", "localField": "tag", "foreignField": "tag", "as": "name"}},
            {"$set": {"name": "$name.name"}}
        ]
        results = await self.bot.leaderboard_db.aggregate(pipeline).to_list(length=None)
        text = ""
        x = 0
        embeds: list[disnake.Embed] = []
        for result in results:
            cc: str = result.get('country_code')
            flag = f":flag_{cc.lower()}:"
            name = result.get('name')
            if not name:
                continue
            text += f"`{self.bot.clean_string(text=result.get('name')[0])[:15]:15}`{flag}{result.get('country_name')}\n"
            x += 1
            if x == 50:
                x = 0
                embeds.append(disnake.Embed(title=f"{ctx.guild.name} Player Countries", description=text))
                text = ""

        if x != 0:
            embeds.append(disnake.Embed(title=f"{ctx.guild.name} Player Countries", description=text))
        if sum([len(embed.description) for embed in embeds] + [len(embed.title) for embed in embeds]) >= 5950:
            for embed in embeds:
                await ctx.followup.send(embed=embed)
        else:
            await ctx.send(embeds=embeds)

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
                               townhall: List[int] = commands.Param(default=None, convert_defaults=True, converter=th_convertor),
                               server: disnake.Guild = commands.Param(converter=server_converter, default=None),
                               limit: int = commands.Param(default=50, max_value=50)):

        guild = server if server is not None else ctx.guild
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)
        top_50 = await self.bot.player_stats.find({"$and" : [{"tag" :  {"$in": member_tags}}, {"townhall" : {"$in" : townhall}}]}, {"tag" : 1}).sort(f"donations.{season}.donated", -1).limit(limit).to_list(length=50)
        players = await self.bot.get_players(tags=[p["tag"] for p in top_50])
        graph, total_donos, total_received = await graph_creator.create_clan_donation_graph(bot=self.bot, clans=clans, season=season, type="donated", townhalls=townhall)
        embed = await shared_embeds.donation_board(bot=self.bot, players=players, season=season, title_name=f"{guild.name}", type="donations",
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
        member_tags = self.bot.get_family_member_tags(guild_id=guild.id)
        distinct = await self.bot.player_stats.distinct("tag", filter={"tag": {"$in": member_tags}})
        players = await self.bot.get_players(tags=distinct)
        embed: disnake.Embed = await shared_embeds.capital_donation_board(bot=self.bot, players=[player for player in players if player.town_hall in townhall], week=week,
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

    @family.sub_command(name="progress", description="Top 50 Progress for family members")
    async def progress(self, ctx: disnake.ApplicationCommandInteraction,
                       type=commands.Param(choices=["Heroes & Pets", "Troops, Spells, & Sieges", "Loot"]),
                       season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                       server: disnake.Guild = commands.Param(converter=server_converter, default=None),
                       limit: int = commands.Param(default=50, min_value=1, max_value=50)):
        """
            Parameters
            ----------
            type: progress type
            season: clash season to view data for
            server: server to view
            limit: change amount of results shown
        """
        buttons = []
        guild = server if server is not None else ctx.guild
        footer_icon = guild.icon.url if guild.icon is not None else self.bot.user.avatar.url
        member_tags = await self.bot.get_family_member_tags(guild_id=guild.id)
        if type == "Heroes & Pets":
            embed = await shared_embeds.hero_progress(bot=self.bot, player_tags=member_tags,
                                                      season=season,
                                                      footer_icon=footer_icon,
                                                      title_name=f"{guild.name} {type} Progress", limit=limit)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.magnify_glass.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"fmp_{season}_{limit}_{guild.id}_heroes"))
        elif type == "Troops, Spells, & Sieges":
            embed = await shared_embeds.troops_spell_siege_progress(bot=self.bot,
                                                                    player_tags=member_tags,
                                                                    season=season,
                                                                    footer_icon=footer_icon,
                                                                    title_name=f"{guild.name} {type} Progress",
                                                                    limit=limit)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.magnify_glass.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"fmp_{season}_{limit}_{guild.id}_troopsspells"))
        elif type == "Loot":
            embed = await shared_embeds.loot_progress(bot=self.bot,
                                                      player_tags=member_tags,
                                                      season=season,
                                                      footer_icon=footer_icon,
                                                      title_name=f"{guild.name} {type} Progress",
                                                      limit=limit)

        await ctx.edit_original_message(embed=embed, components=[buttons] if buttons else [])

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
    @countries.autocomplete("server")
    @progress.autocomplete("server")
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
    @progress.autocomplete("season")
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

def setup(bot: CustomClient):
    bot.add_cog(FamCommands(bot))


