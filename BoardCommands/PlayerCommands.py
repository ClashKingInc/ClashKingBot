import disnake
import calendar
import coc

from utils.clash import heros, heroPets
from disnake.ext import commands
from typing import List
from utils.search import search_results
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import interaction_handler
from utils.player_pagination import button_pagination
from Exceptions.CustomExceptions import *
from DiscordLevelingCard import RankCard, Settings
from operator import attrgetter
from utils.constants import LEVELS_AND_XP

from BoardCommands.Utils import Shared as shared_embeds
from BoardCommands.Utils import Graphs as graph_creator
from BoardCommands.Utils import Player as player_embeds

class PlayerCommands(commands.Cog):
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

    @commands.slash_command(name="game-rank", description="Get xp rank for in game activities")
    async def game_rank(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        await ctx.response.defer()
        if member is None:
            self.author = ctx.author
            member = self.author

        custom = await self.bot.level_cards.find_one({"user_id": ctx.author.id})
        if custom is not None:
            background_color = custom.get("background_color") if custom.get(
                "background_color") is not None else "#36393f"
            background = custom.get("background_image") if custom.get(
                "background_image") is not None else "https://media.discordapp.net/attachments/923767060977303552/1067289914443583488/bgonly1.jpg"
            text_color = custom.get("text_color") if custom.get("text_color") is not None else "white"
            bar_color = custom.get("bar_color") if custom.get("bar_color") is not None else "#b5cf3d"
        else:
            background_color = "#36393f"
            background = "https://media.discordapp.net/attachments/923767060977303552/1067289914443583488/bgonly1.jpg"
            text_color = "white"
            bar_color = "#b5cf3d"

        card_settings = Settings(
            background_color=background_color,
            background=background,
            text_color=text_color,
            bar_color=bar_color
        )

        def _find_level(current_total_xp: int):
            # check if the current xp matches the xp_needed exactly
            if current_total_xp in LEVELS_AND_XP.values():
                for level, xp_needed in LEVELS_AND_XP.items():
                    if current_total_xp == xp_needed:
                        return int(level)
            else:
                for level, xp_needed in LEVELS_AND_XP.items():
                    if 0 <= current_total_xp <= xp_needed:
                        level = int(level)
                        level -= 1
                        if level < 0:
                            level = 0
                        return level

        linked_accounts: List[MyCustomPlayer] = await search_results(self.bot, str(member.id))
        if linked_accounts == []:
            return await ctx.send(content="No Linked Acccounts")

        top_account = max(linked_accounts, key=attrgetter('level_points'))
        print(f"{top_account.name} | {top_account.tag}")
        level = int(max(_find_level(current_total_xp=top_account.level_points), 0))
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        results = await self.bot.player_stats.find({"clan_tag": {"$in": clan_tags}}).sort("points", -1).to_list(1500)
        rank = None
        for r, result in enumerate(results, 1):
            if result.get("tag") == top_account.tag:
                rank = r
                break

        rank_card = RankCard(
            settings=card_settings,
            avatar=member.display_avatar.url,
            level=level,
            current_exp=top_account.level_points,
            max_exp=LEVELS_AND_XP[str(level + 1)],
            username=f"{member}", account=top_account.name[:13],
            rank=rank
        )
        image = await rank_card.card3()
        await ctx.edit_original_message(file=disnake.File(image, filename="rank.png"))


    @player.sub_command(name="donations", description="Donations for all of a player's accounts")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None,
                        season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        if discord_user is None:
            discord_user = ctx.author
        players: List[MyCustomPlayer] = await search_results(self.bot, str(discord_user.id))
        if not players:
            raise NoLinkedAccounts

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        footer_icon = discord_user.display_avatar.url
        embed: disnake.Embed = await board_cog.donation_board(players=players, season=season, footer_icon=footer_icon, title_name=f"{discord_user.display_name}", type="donations")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"donatedplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"receivedplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"ratioplayer_{season}_{discord_user.id}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])


    @player.sub_command(name="capital", description="Capital stats for a player or a user's accounts")
    async def capital(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str= None, discord_user: disnake.Member = None):
        pass


    @player.sub_command(name="upgrades", description="Show upgrades left for an account")
    async def upgrades(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str= None, discord_user: disnake.Member = None):
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        players = await search_results(self.bot, search_query)
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


    @player.sub_command(name="search", description="Search for players")
    async def search(self, ctx: disnake.ApplicationCommandInteraction, clan:str = commands.Param(choices=["No Clan", "In Clan"], default=None),
                     league: str = commands.Param(choices=["No League", "Has League"], default=None),
                     townhall: int = commands.Param(default=None, gt=8), trophies: int = None, war_stars:int = None, clan_capital_donos: int = None, attacks: int = None):
        msg = await ctx.original_message()
        while True:
            embed, buttons = await self.create_search(clan=clan, townhall=townhall, trophies=trophies, war_stars=war_stars, clan_capital_donos=clan_capital_donos,
                                                      league=league, attacks=attacks)
            await ctx.edit_original_message(embed=embed, components=buttons)
            try:
                res = await interaction_handler(bot=self.bot, ctx=ctx)
            except:
                await msg.edit(components=[])




    '''@player.sub_command(name="activity", description="Activity stats for all of a player's accounts")
    async def activity(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None,
                       season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        if discord_user is None:
            discord_user = ctx.author
        players: List[MyCustomPlayer] = await search_results(self.bot, str(discord_user.id))
        if not players:
            raise NoLinkedAccounts

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        footer_icon = discord_user.display_avatar.url
        embed: disnake.Embed = await board_cog.activity_board(players=players, season=season, footer_icon=footer_icon,title_name=f"{discord_user.display_name}")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"activityplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Last Online", emoji=self.bot.emoji.clock.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"lastonlineplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Graph", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"activitygraphplayer_{season}_{discord_user.id}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])'''



    #@activity.autocomplete("season")
    @donations.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]

def setup(bot: CustomClient):
    bot.add_cog(PlayerCommands(bot))