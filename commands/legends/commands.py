import coc.utils
import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from discord import autocomplete, convert, options
from exceptions.CustomExceptions import PlayerNotInLegends
from utility.constants import POSTER_LIST

from .utils import (
    legend_buckets,
    legend_clan,
    legend_cutoff,
    legend_day_overview,
    legend_eos_finishers,
    legend_history,
    legend_poster,
    legend_streaks,
)


class Legends(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(
        name=disnake.Localized('legends', key='legends-name'),
        description=disnake.Localized(key='legends-description'),
    )
    async def legends(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @legends.sub_command(
        name=disnake.Localized('search', key='search-name'),
        description=disnake.Localized(key='search-description'),
    )
    async def legends_search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(
            autocomplete=autocomplete.legend_players,
            converter=convert.player,
            description=disnake.Localized(key='player-autocomplete-description'),
        ),
    ):
        """
        Parameters
        ----------
        player: player to get legends info on
        """

        if player.league.name != 'Legend League':
            raise PlayerNotInLegends

        _, locale = self.bot.get_localizator(ctx=ctx)
        # make sure player has unpaused tracking
        await self.bot.player_stats.update_one({'tag': player.tag}, {'$set': {'paused': False}})
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await legend_day_overview(bot=self.bot, player=player, embed_color=embed_color, locale=locale)
        buttons = [
            disnake.ui.Button(
                label=_('today'),
                style=disnake.ButtonStyle.grey,
                custom_id=f'legendday:{player.tag}',
            ),
            disnake.ui.Button(
                label='',
                emoji=self.bot.emoji.calendar.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'legendseason:{player.tag}',
            ),
            disnake.ui.Button(
                label='',
                emoji=self.bot.emoji.clock.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=f'legendhistory:{player.tag}',
            ),
            disnake.ui.Button(
                label='➕',
                style=disnake.ButtonStyle.grey,
                custom_id=f'legendquick:ctx:{player.tag}',
            ),
        ]
        await ctx.send(embed=embed, components=buttons)

    @legends.sub_command(
        name=disnake.Localized('clan', key='clan-name'),
        description=disnake.Localized(key='clan-description'),
    )
    async def legends_clan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = options.clan):
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await legend_clan(bot=self.bot, clan=clan, embed_color=embed_color)
        await ctx.send(embed=embed)

    @legends.sub_command(
        name=disnake.Localized('history', key='history-name'),
        description=disnake.Localized(key='history-description'),
    )
    async def legend_history(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player),
    ):
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        embed = await legend_history(bot=self.bot, player=player, embed_color=embed_color)
        await ctx.send(embed=embed)

    @legends.sub_command(
        name='poster',
        description='Poster w/ graph & stats to show off season legends stats',
    )
    async def legend_poster(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        player: coc.Player = commands.Param(autocomplete=autocomplete.legend_players, converter=convert.player),
        background: str = commands.Param(default=None, choices=list(POSTER_LIST.keys())),
    ):
        poster: disnake.File = await legend_poster(bot=self.bot, player=player, background=background)
        await ctx.send(file=poster)

    @legends.sub_command(name='stats', description='View various legend related stats')
    async def legend_stats(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        type: str = commands.Param(choices=['Rank Cutoff', 'Triple Streaks', 'Trophy Buckets', 'EOS Finishers']),
        limit: int = commands.Param(default=50, min_value=1, max_value=50),
    ):
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        if type == 'Rank Cutoff':
            embed = await legend_cutoff(bot=self.bot, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'legendcutoff:',
                )
            )
        elif type == 'Triple Streaks':
            embed = await legend_streaks(bot=self.bot, limit=limit, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'legendstreaks:{limit}',
                )
            )
        elif type == 'Trophy Buckets':
            embed = await legend_buckets(bot=self.bot, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'legendbuckets:',
                )
            )
        elif type == 'EOS Finishers':
            embed = await legend_eos_finishers(bot=self.bot, embed_color=embed_color)
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(
                    label='',
                    emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f'legendeosfinishers:',
                )
            )
        await ctx.edit_original_message(embed=embed, components=[buttons])


def setup(bot):
    bot.add_cog(Legends(bot))
