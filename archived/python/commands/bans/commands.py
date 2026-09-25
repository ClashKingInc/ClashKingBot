import coc
import disnake
from disnake import Localized as Loc
from disnake.ext import commands

from classes.bot import CustomClient
from discord import options
from exceptions.CustomExceptions import MessageException
from utility.components import create_components
from utility.discord_utils import check_commands, interaction_handler

from .utils import add_ban, create_embeds, remove_ban


class Bans(commands.Cog, name='Bans'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='ban', description=Loc(key='ban-description'))
    async def ban(self, ctx):
        await ctx.response.defer()

    @ban.sub_command(name='add', description=Loc(key='add-description'))
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_add(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = options.family_player,
        reason: str = commands.Param(name=Loc(key='reason-option'), description=Loc(key='reason-description'), default=None),
        dm_player: str = commands.Param(name=Loc(key='dm-player-option'), description=Loc(key='dm-player-description'), default=None),
    ):
        _, locale = self.bot.get_localizator(ctx=ctx)
        embed = await add_ban(
            bot=self.bot, player=player, added_by=ctx.user, guild=ctx.guild, reason=reason, rollover_days=None, dm_player=dm_player, locale=locale
        )
        await ctx.edit_original_message(embed=embed)

    @ban.sub_command(name='remove', description=Loc(key='remove-description'))
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_remove(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = options.banned_player,
    ):
        _, locale = self.bot.get_localizator(ctx=ctx)
        embed = await remove_ban(bot=self.bot, player=player, removed_by=ctx.user, guild=ctx.guild, locale=locale)
        await ctx.edit_original_message(embed=embed)

    @ban.sub_command(name='list', description=Loc(key='list-description'))
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def ban_list(self, ctx: disnake.ApplicationCommandInteraction):

        _, locale = self.bot.get_localizator(ctx=ctx)

        bans = await self.bot.banlist.find({'server': ctx.guild.id}).to_list(length=None)
        if not bans:
            raise MessageException(_('no-banned-players'))

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embeds = await create_embeds(bot=self.bot, bans=bans, guild=ctx.guild, embed_color=embed_color, locale=locale)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)

            if res.data.custom_id == 'Previous':
                current_page -= 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Next':
                current_page += 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == 'Print':
                for embed in embeds:
                    await ctx.channel.send(embed=embed)
                await ctx.delete_original_message()


def setup(bot: CustomClient):
    bot.add_cog(Bans(bot))
