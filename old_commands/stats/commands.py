import coc
import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from discord import options

from .utils import war_hitrate


class StatCommands(commands.Cog, name='Stat Commands'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name='stats')
    async def stats(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({'discord_user': ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get('private_mode', False)
        if 'board' in ctx.filled_options.keys():
            ephemeral = True
        await ctx.response.defer(ephemeral=ephemeral)

    @stats.sub_command(name='war', description='War stats for a family or clan')
    async def war(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        type: str = commands.Param(choices=['Hit Rate', 'Defense Rate', 'Attack Info']),
        clan: coc.Clan = options.optional_clan,
        server: disnake.Guild = options.optional_family,
        war_types: str = commands.Param(default='All', choices=['All', 'CWL', 'Friendly', 'War', 'War & CWL']),
        th_filter: str = commands.Param(default='All', autocomplete=autocomplete.th_filters),
        star_filter: str = commands.Param(
            default='3',
            description="Comma seperated list (default: '3', example: '3, 2, 1')",
        ),
        min_attacks: int = commands.Param(default=5, min_value=1, max_value=100, description='default 5'),
        season: str = options.optional_season,
        num_wars: int = None,
        num_days: int = None,
        limit: int = commands.Param(default=50, min_value=1, max_value=50),
    ):
        if clan is None:
            server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        if type == 'Hit Rate':
            embed = await war_hitrate(
                bot=self.bot,
                clan=clan,
                server=server,
                th_filter=th_filter.replace(' ', '').lower(),
                star_filter=star_filter,
                limit=limit,
                min_attacks=min_attacks,
                war_types=war_types.replace(' ', '').lower(),
                season=season,
                num_wars=num_wars,
                num_days=num_days,
                embed_color=embed_color,
            )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(StatCommands(bot))
