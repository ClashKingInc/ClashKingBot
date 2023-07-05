import datetime
import time

import disnake
import coc
import calendar

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.Enums import TrophySort
from Exceptions.CustomExceptions import InvalidGuildID
from typing import List
from utils.general import get_clan_member_tags
from utils.ClanCapital import gen_raid_weekend_datestrings
from pytz import utc
from BoardCommands.Utils import Shared as shared_embeds
from BoardCommands.Utils import Graphs as graph_creator
from BoardCommands.Utils import Family as family_embeds


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
        if "board" in ctx.filled_options.keys():
            ephemeral = True
        await ctx.response.defer(ephemeral=ephemeral)

    '''@commands.slash_command(name="countries")
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
            await ctx.send(embeds=embeds)'''


    @family.sub_command(name="clans", description="Overview list of all family clans")
    async def family_clans(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await family_embeds.create_family_clans(bot=self.bot, guild=guild)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"famclans_{guild.id}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @family.sub_command(name="compo", description="Composition of a family. (with a twist?)")
    async def family_compo(self, ctx: disnake.ApplicationCommandInteraction,
                           type: str = commands.Param(default="Totals", choices=["Totals", "Hitrate"]),
                           server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            type: type of compo calculation
            server: a discord server
        """
        guild = server if server else ctx.guild
        guild_icon = guild.icon.url if guild.icon else self.bot.user.avatar.url
        member_tags = await self.bot.get_family_member_tags(guild_id=guild.id)

        if type == "Totals":
            embed = await shared_embeds.th_composition(bot=self.bot,
                                                       player_tags=member_tags,
                                                       title=f"{guild.name} Townhall Composition",
                                                       thumbnail=guild_icon)
            custom_id = f"famcompo_{guild.id}"
        elif type == "Hitrate":
            embed = await shared_embeds.th_hitrate(bot=self.bot,
                                                   player_tags=member_tags,
                                                   title=f"{guild.name} TH Hitrate Compo",
                                                   thumbnail=guild_icon)
            custom_id = f"famhrcompo_{guild.id}"

        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=custom_id))

        await ctx.edit_original_message(embed=embed, components=buttons)


    @family.sub_command(name="wars", description="List of current wars by family clans")
    async def family_wars(self, ctx: disnake.ApplicationCommandInteraction,
                          server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await family_embeds.create_wars(bot=self.bot, guild=guild)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"famwars_{guild.id}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @family.sub_command(name="board", description="Image Board")
    async def board(self, ctx: disnake.ApplicationCommandInteraction,
                    board: str = commands.Param(choices=["Activity", "Legends", "Trophies"]),
                    server: disnake.Guild = commands.Param(converter=server_converter, default=None)):

        guild = server if server is not None else ctx.guild
        guild_icon = guild.icon.url if guild.icon else self.bot.user.avatar.url

        if board == "Activity":
            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            top_50 = await self.bot.player_stats.find({"tag": {"$in": member_tags}}, {"tag": 1}).sort(f"donations.{self.bot.gen_season_date()}.donated", -1).limit(30).to_list(length=50)
            players = await self.bot.get_players(tags=[p["tag"] for p in top_50], custom=True)
            players.sort(key=lambda x: x.donos().donated, reverse=False)
            file = await shared_embeds.image_board(bot=self.bot, players=players, logo_url=guild_icon,
                                                   title=f'{guild.name} Activity/Donation Board',
                                                   season=self.bot.gen_season_date(), type="activities")
            board_type = "famboardact"
        elif board == "Legends":
            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            top_50 = await self.bot.player_cache.find({"$and" : [{"tag": {"$in": member_tags}}, {"data.league.name" : "Legend League"}]},
                                                      {"tag": 1}).sort(f"data.trophies", -1).limit(30).to_list(length=40)
            players = await self.bot.get_players(tags=[p["tag"] for p in top_50], custom=True)
            players.sort(key=lambda x: x.trophies, reverse=False)
            file = await shared_embeds.image_board(bot=self.bot, players=players, logo_url=guild_icon,
                                                   title=f'{guild.name} Legend Board', type="legend")
            board_type = "famboardlegend"

        elif board == "Trophies":
            clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
            clans: List[coc.Clan] = await self.bot.get_clans(tags=clan_tags)
            member_tags = get_clan_member_tags(clans=clans)
            top_50 = await self.bot.player_cache.find({"tag": {"$in": member_tags}}, {"tag": 1}).sort(f"data.trophies", -1).limit(30).to_list(length=50)
            players = await self.bot.get_players(tags=[p["tag"] for p in top_50], custom=True)
            players.sort(key=lambda x: x.trophies, reverse=False)
            file = await shared_embeds.image_board(bot=self.bot, players=players, logo_url=guild_icon,
                                                   title=f'{guild.name} Trophy Board', type="trophies")
            board_type = "famboardtrophies"

        await ctx.edit_original_message(content="Image Board Created!")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"{board_type}_{guild.id}"))
        await ctx.channel.send(file=file, components=[buttons])


    @family.sub_command(name="leagues", description="List of clans by cwl or capital league")
    async def family_leagues(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await family_embeds.create_leagues(bot=self.bot, guild=guild, type="CWL")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="CWL", emoji=self.bot.emoji.cwl_medal.partial_emoji,
                              style=disnake.ButtonStyle.green,
                              custom_id=f"cwlleaguesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.grey, custom_id=f"capitalleaguesfam_{guild.id}"))
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
        member_tags = await self.bot.get_family_member_tags(guild_id=guild.id)
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

        #graph = await graph_creator.create_capital_graph(bot=self.bot, all_players=players, clans=clans, week=week, type="donations", server_id=guild.id)
        #embed.set_image(url=f"{graph}?{int(datetime.datetime.now().timestamp())}")
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
            buttons.append_item(disnake.ui.Button(
                label="", emoji=self.bot.emoji.magnify_glass.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"fmp_{season}_{limit}_{guild.id}_lootprogress"))

        await ctx.edit_original_message(embed=embed, components=[buttons] if buttons else [])


    @family.sub_command(name="clan-games", description="Top Clan Games Points in Family")
    async def clan_games(self, ctx: disnake.ApplicationCommandInteraction,
                         season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                         server: disnake.Guild = commands.Param(converter=server_converter, default=None),
                         limit: int = commands.Param(default=50, min_value=1, max_value=50)):
        guild = server if server is not None else ctx.guild
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        members = await self.bot.player_stats.distinct("tag", filter={f"clan_tag": {"$in": clan_tags}})
        did_games_in_clan = await self.bot.player_stats.distinct("tag", filter={f"clan_games.{season}.clan": {"$in" : clan_tags}})

        all_tags = members + did_games_in_clan
        all_tags = [r["tag"] for r in (await self.bot.player_stats.find({"tag": {"$in": all_tags}}).sort(f"clan_games.{season}.clan",-1).limit(limit).to_list(length=limit))]

        players = await self.bot.get_players(tags=all_tags)
        embed = await shared_embeds.create_clan_games(bot=self.bot, players=players, season=season, clan_tags=clan_tags,
                                                      title_name=f"{guild.name} Top {limit} Clan Games Points", limit=limit)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.clan_games.partial_emoji,
                              style=disnake.ButtonStyle.grey,
                              custom_id=f"clangamesfam_{season}_{limit}_{guild.id}"))
        await ctx.edit_original_message(embed=embed, components=[buttons])


    @family.sub_command(name="history", description="History of certain stats for the season")
    async def family_history(self, ctx: disnake.ApplicationCommandInteraction,
                             type= commands.Param(choices=["Join/Leave"]),
                             season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor),
                             server: disnake.Guild = commands.Param(converter=server_converter, default=None)):

        guild = server if server is not None else ctx.guild
        if type == "Join/Leave":
            embed: disnake.Embed = await family_embeds.create_joinhistory(bot=self.bot, guild=guild, season=season)
        await ctx.edit_original_message(embed=embed, components=None)


    @family.sub_command(name="trophies", description="List of clans by home, builder, or capital trophy points")
    async def trophies(self, ctx: disnake.ApplicationCommandInteraction, server: disnake.Guild = commands.Param(converter=server_converter, default=None)):
        guild = server if server is not None else ctx.guild
        embed = await family_embeds.create_trophies(bot=self.bot, guild=guild, sort_type=TrophySort.home)
        buttons = disnake.ui.ActionRow()
        sort_type = TrophySort.home
        buttons.append_item(disnake.ui.Button(label="Home", emoji=self.bot.emoji.trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.home else disnake.ButtonStyle.grey,custom_id=f"hometrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Versus", emoji=self.bot.emoji.versus_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.versus else disnake.ButtonStyle.grey, custom_id=f"versustrophiesfam_{guild.id}"))
        buttons.append_item(disnake.ui.Button(label="Capital", emoji=self.bot.emoji.capital_trophy.partial_emoji,
                                              style=disnake.ButtonStyle.green if sort_type == TrophySort.capital else disnake.ButtonStyle.grey,
                                              custom_id=f"capitaltrophiesfam_{guild.id}"))
        await ctx.edit_original_message(embed=embed, components=buttons)


    @family_clans.autocomplete("server")
    @family_leagues.autocomplete("server")
    @family_donations.autocomplete("server")
    @family_capital.autocomplete("server")
    @progress.autocomplete("server")
    @board.autocomplete("server")
    @family_compo.autocomplete("server")
    @family_wars.autocomplete("server")
    @clan_games.autocomplete("server")
    @family_history.autocomplete("server")
    @trophies.autocomplete("server")
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
    @clan_games.autocomplete("season")
    @family_history.autocomplete("season")
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


