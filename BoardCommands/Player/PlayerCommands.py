import disnake
import calendar
import coc

from disnake.ext import commands
from typing import TYPE_CHECKING, List
from utils.search import search_results
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import *
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
else:
    cog_class = commands.Cog

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
        embed: disnake.Embed = await board_cog.donation_board(players=players, season=season, footer_icon=footer_icon, title_name=f"{discord_user.display_name}")
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