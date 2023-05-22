import disnake
import calendar
import coc

from utils.clash import heros, heroPets
from disnake.ext import commands
from typing import TYPE_CHECKING, List
from utils.search import search_results
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import *
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
    from PlayerCog import PlayerCog
    player_cog = PlayerCog
else:
    cog_class = commands.Cog
    player_cog = commands.Cog

class PlayerCommands(player_cog):
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

        results = await search_results(self.bot, search_query)
        embed = self.create_upgrade_embed(results[0])
        components = []
        if len(results) > 1:
            player_results = []
            for count, player in enumerate(results):
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
            embed = upgrade_embed(self.bot, results[current_page])
            await res.edit_original_message(embeds=embed)



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










    @player.sub_command(name="activity", description="Activity stats for all of a player's accounts")
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

        await ctx.edit_original_message(embed=embed, components=[buttons])


    @donations.autocomplete("season")
    @activity.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]