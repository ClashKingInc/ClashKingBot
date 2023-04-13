import disnake
import pytz

from disnake.ext import commands

from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import InvalidGuildID

from typing import TYPE_CHECKING

tiz = pytz.utc
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    from FamilyCog import FamilyCog
    board_cog = BoardCog
    family_cog = FamilyCog
else:
    board_cog = commands.Cog
    family_cog = commands.Cog

class FamCommands(family_cog):

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

    @commands.slash_command(name="family")
    async def family(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user": ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)

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


    @family_clans.autocomplete("server")
    @family_leagues.autocomplete("server")
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



