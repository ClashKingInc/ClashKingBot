import math
import coc

import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from classes.player.stats import LegendRanking
from discord import autocomplete, options
from exceptions.CustomExceptions import ExpiredComponents, NoLinkedAccounts, MessageException
from utility.components import button_generator
from .utils import best_eos

class Ranked(commands.Cog, name='Family Trophy Stats'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(
        name='ranked',
        description="Commands for ranked stats",
        install_types=disnake.ApplicationInstallTypes.all(),
        contexts=disnake.InteractionContextTypes.all(),
    )
    async def ranked(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            type: str = commands.Param(choices=["Players", "Clans"]),
    ):
        await ctx.response.defer()


    @ranked.sub_command(name='players', description='Region rankings for players on server')
    async def ranked_players(self, ctx: disnake.ApplicationCommandInteraction):

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))


    @ranked.sub_command(name='clans', description='Region rankings for clans on server')
    async def ranked_clans(self, ctx: disnake.ApplicationCommandInteraction):


        await ctx.edit_original_message(embed=embed)



    @commands.slash_command(
        name='best-eos',
        description='Arranges players to create best clans if EOS was now',
        install_types=disnake.ApplicationInstallTypes.all(),
        contexts=disnake.InteractionContextTypes.all(),
    )
    async def best(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            type: str = commands.Param(choices=["Home Village", "Builder Base"]),
            country: str = commands.Param(autocomplete=autocomplete.country_names, default=None),
            server: disnake.Guild = options.optional_family,
    ):
        guild_id = getattr(server or ctx.guild, "id", None)
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=guild_id)
        embed = await best_eos(bot=self.bot, type=type, country=country, server_id=guild_id, embed_color=embed_color)
        button = button_generator(
            bot=self.bot,
            button_id=f"besteos:{guild_id}:{type}:{country}",
        )
        await ctx.send(embed=embed, components=button)




def setup(bot: CustomClient):
    bot.add_cog(Ranked(bot))
