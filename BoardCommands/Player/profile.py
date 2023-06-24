from datetime import date, timedelta, datetime
from disnake.ext import commands
from BoardCommands.Player.profile_embeds import *
from Assets.emojiDictionary import emojiDictionary
from BoardCommands.Player.pagination import button_pagination
from utils.search import search_results
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from utils.troop_methods import heros, heroPets
from Assets.thPicDictionary import thDictionary
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List
from DiscordLevelingCard import RankCard, Settings
from operator import attrgetter
from utils.discord_utils import interaction_handler
from collections import defaultdict
from coc.raid import RaidMember, RaidLogEntry
from utils.constants import LEVELS_AND_XP

import asyncio
import operator
import calendar
import pytz
utc = pytz.utc

class profiles(commands.Cog, name="Profile"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
    @commands.slash_command(name="player")
    async def player(self, ctx):
        pass







    @player.sub_command(name="war-stats", description="War stats of a player or discord user")
    async def war_stats_player(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str=None, discord_user:disnake.Member=None, start_date = 0, end_date = 9999999999):
        """
            Parameters
            ----------
            player_tag: (optional) player to view war stats on
            discord_user: (optional) discord user's accounts to view war stats of
            start_date: (optional) filter stats by date, default is to view this season
            end_date: (optional) filter stats by date, default is to view this season
        """
        await ctx.response.defer()
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

        players = await search_results(self.bot, search_query)
        if players == []:
            embed = disnake.Embed(description="**No matching player/discord user found**", colour=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.create_player_hr(player=players[0], start_date=start_date, end_date=end_date)
        await ctx.edit_original_message(embed=embed, components=self.player_components(players))
        if len(players) == 1:
            return
        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            page = int(res.values[0])
            embed = await self.create_player_hr(player=players[page], start_date=start_date, end_date=end_date)
            await res.edit_original_message(embed=embed)








    @player.sub_command(name="to-do", description="Get a list of things to be done (war attack, legends hits, capital raids etc)")
    async def to_do(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member=None):
        await ctx.response.defer()
        if discord_user is None:
            discord_user = ctx.author
        linked_accounts = await search_results(self.bot, str(discord_user.id))
        embed = await self.to_do_embed(discord_user=discord_user, linked_accounts=linked_accounts)
        await ctx.edit_original_message(embed=embed)





    # UTILS








def setup(bot: CustomClient):
    bot.add_cog(profiles(bot))