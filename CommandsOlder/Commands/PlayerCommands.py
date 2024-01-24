import disnake
import calendar
import coc

from disnake.ext import commands
from typing import List
from classes.player import MyCustomPlayer
from classes.bot import CustomClient
from exceptions.CustomExceptions import *
from DiscordLevelingCard import RankCard, Settings
from operator import attrgetter
from datetime import date, timedelta, datetime

from utility.discord_utils import interaction_handler
from utility.player_pagination import button_pagination
from utility.components import player_components
from utility.search import search_results
from utility.constants import LEVELS_AND_XP

from BoardCommands.Utils import Shared as shared_embeds
from BoardCommands.Utils import Player as player_embeds


class PlayerCommands(commands.Cog, name="Player Commands"):
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



    @commands.slash_command(name="player")
    async def player(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user": ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)


    @player.sub_command(name="lookup", description="Lookup a player or discord user")
    async def lookup(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str = None, discord_user:disnake.Member=None):
        """
            Parameters
            ----------
            player_tag: (optional) tag to lookup
            discord_user: (optional) discord user to lookup
        """
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)
        results = await search_results(self.bot, search_query)
        results = results[:25]
        if results == []:
            return await ctx.edit_original_message(content="No results were found.", embed=None)
        msg = await ctx.original_message()
        await button_pagination(self.bot, ctx, msg, results)


    @player.sub_command(name="accounts", description="List of accounts a user has & combined stats")
    async def list(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None):
        discord_user = discord_user if discord_user is not None else ctx.author

        results = await search_results(self.bot, str(discord_user.id))
        if not results:
            raise NoLinkedAccounts

        embed = await player_embeds.create_player_list(bot=self.bot, players=results, discord_user=discord_user)

        await ctx.edit_original_message(embed=embed)



    @player.sub_command(name="upgrades", description="Show upgrades left for an account")
    async def upgrades(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str= None, discord_user: disnake.Member = None):
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        players = (await search_results(self.bot, search_query))[:25]
        embed = await player_embeds.upgrade_embed(self.bot, players[0])
        components = []
        if len(players) > 1:
            player_results = []
            for count, player in enumerate(players):
                player_results.append(
                    disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                         value=f"{count}"))
            profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)
            st2 = disnake.ui.ActionRow()
            st2.append_item(profile_select)
            components = [st2]
        await ctx.send(embeds=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                     timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break

            await res.response.defer()
            current_page = int(res.values[0])
            embed = await player_embeds.upgrade_embed(self.bot, players[current_page])
            await res.edit_original_message(embeds=embed)


    @player.sub_command(name="to-do", description="Get a list of things to be done (war attack, legends hits, capital raids etc)")
    async def to_do(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None):
        if discord_user is None:
            discord_user = ctx.author
        linked_accounts = await search_results(self.bot, str(discord_user.id))
        if not linked_accounts:
            raise NoLinkedAccounts
        embed = await player_embeds.to_do_embed(bot=self.bot, discord_user=discord_user, linked_accounts=linked_accounts)
        await ctx.edit_original_message(embed=embed)


    @player.sub_command(name="war-stats", description="War stats of a player or discord user")
    async def war_stats_player(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str = None,
                               discord_user: disnake.Member = None, start_date=0, end_date=9999999999):
        """
            Parameters
            ----------
            player_tag: (optional) player to view war stats on
            discord_user: (optional) discord user's accounts to view war stats of
            start_date: (optional) filter stats by date, default is to view this season
            end_date: (optional) filter stats by date, default is to view this season
        """
        if start_date != 0 and end_date != 9999999999:
            start_date = int(datetime.strptime(start_date, "%d %B %Y").timestamp())
            end_date = int(datetime.strptime(end_date, "%d %B %Y").timestamp())
        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        players = (await search_results(self.bot, search_query))[:25]
        if not players:
            embed = disnake.Embed(description="**No matching player/discord user found**", colour=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await player_embeds.create_player_hr(bot=self.bot, player=players[0], start_date=start_date, end_date=end_date)
        await ctx.edit_original_message(embed=embed, components=player_components(players))
        if len(players) == 1:
            return
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            page = int(res.values[0])
            embed = await player_embeds.create_player_hr(bot=self.bot, player=players[page], start_date=start_date, end_date=end_date)
            await res.edit_original_message(embed=embed)


    @player.sub_command(name="stats", description="Get stats for different areas of a player")
    async def player_stats(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member, type:str =commands.Param(choices=["CWL", "Raids"])):
        if type == "Raids":
            return await player_embeds.raid_stalk(bot=self.bot, ctx=ctx, member=member)
        elif type == "CWL":
            return await player_embeds.cwl_stalk(bot=self.bot,ctx=ctx, member=member)



    # AUTOCOMPLETES
    @war_stats_player.autocomplete("start_date")
    @war_stats_player.autocomplete("end_date")
    async def date_autocomp(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        today = date.today()
        date_list = [today - timedelta(days=day) for day in range(365)]
        return [dt.strftime("%d %B %Y") for dt in date_list if query.lower() in str(dt.strftime("%d %B, %Y")).lower()][:25]

    @lookup.autocomplete("player_tag")
    @upgrades.autocomplete("player_tag")
    @war_stats_player.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names

    @donations.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

def setup(bot: CustomClient):
    bot.add_cog(PlayerCommands(bot))