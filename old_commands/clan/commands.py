import coc
import disnake
from disnake import Localized as Loc
from disnake.ext import commands

from classes.bot import CustomClient
from discord import options
from utility.constants import TOWNHALL_LEVELS
from utility.discord.components import button_generator

from .embeds import (
    basic_clan_board,
    clan_donations,
    clan_sorted,
    clan_summary,
    cwl_performance,
    detailed_clan_board,
    minimalistic_clan_board,
    war_log,
)


class ClanCommands(commands.Cog, name='Clan Commands'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(
        name='clan',
        install_types=disnake.ApplicationInstallTypes.all(),
        contexts=disnake.InteractionContextTypes.all(),
    )
    async def clan(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

    @clan.sub_command(
        name='search',
        description=Loc(key='clan-search-description'),
    )
    async def search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan=options.clan,
        type_: str = commands.Param(
            name=Loc(key='option-type'),
            description=Loc(key='clan-search-type-description'),
            default='Detailed',
            choices=[
                Loc('Minimalistic', key='minimalistic'),
                Loc('Basic', key='basic'),
                Loc('Detailed', key='detailed'),
            ],
        ),
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        if type_ == 'Detailed':
            custom_id = f'clandetailed:{clan.tag}'
            embed = await detailed_clan_board(
                bot=self.bot,
                clan=clan,
                server=ctx.guild,
                embed_color=embed_color,
                locale=locale,
            )
        elif type_ == 'Basic':
            custom_id = f'clanbasic:{clan.tag}'
            embed = await basic_clan_board(bot=self.bot, clan=clan, embed_color=embed_color, locale=locale)
        elif type_ == 'Minimalistic':
            custom_id = f'clanmini:{clan.tag}'
            embed = await minimalistic_clan_board(bot=self.bot, clan=clan, embed_color=embed_color, locale=locale)

        buttons = [
            disnake.ui.Button(
                label='',
                emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=custom_id,
            ),
            disnake.ui.Button(
                label=_('open-in-game'),
                url=clan.share_link,
                style=disnake.ButtonStyle.url,
            ),
        ]
        await ctx.edit_original_response(embed=embed, components=[buttons])

    @clan.sub_command(name='donations', description=Loc(key='clan-donations-description'))
    async def donations(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan=options.clan,
        season: str = options.optional_season,
        townhall: int = commands.Param(
            name=Loc(key='option-townhall'),
            description=Loc(key='townhall-description'),
            default=None,
        ),
        limit: int = commands.Param(
            name=Loc(key='option-limit'),
            description=Loc(key='limit-description'),
            default=50,
            min_value=1,
            max_value=50,
        ),
        sort_by: str = commands.Param(
            name=Loc(key='option-sort-by'),
            description=Loc(key='sort-by-description'),
            default='Donations',
            choices=[
                Loc('Name', key='name'),
                Loc('Townhall', key='townhall'),
                Loc('Donations', key='donations'),
                Loc('Received', key='received'),
                Loc('Ratio', key='ratio'),
            ],
        ),
        sort_order: str = commands.Param(
            name=Loc(key='option-sort-order'),
            description=Loc(key='sort-order-description'),
            default='Descending',
            choices=[
                Loc('Ascending', key='ascending'),
                Loc('Descending', key='descending'),
            ],
        ),
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        embed = await clan_donations(
            bot=self.bot,
            clan=clan,
            season=season,
            townhall=townhall,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            embed_color=embed_color,
            locale=locale,
        )

        family_clans = await self.bot.ck_client.get_basic_server_clan_list(server_id=ctx.guild.id)

        components = [
            disnake.ui.Select(
                options=[
                    disnake.SelectOption(
                        label=f'{clan.name} ({clan.tag})',
                        value=f'clandonos:set:clan={clan.tag}',
                    )
                    for clan in family_clans[:25]
                ],
                placeholder='Select Clan',
            ),
            disnake.ui.Select(
                options=[
                    disnake.SelectOption(label=f'Townhall {level}', value=f'clandonos:set:townhall={level}')
                    for level in TOWNHALL_LEVELS
                ]
            ),
        ]

        buttons = button_generator(
            button_id=f'clandonos:{clan.tag}:{season}:{townhall}:{limit}:{sort_by}:{sort_order}',
            bot=self.bot,
        )
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @clan.sub_command(name='war-log', description=Loc(key='clan-warlog-description'))
    async def war(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan=options.clan,
        option: str = commands.Param(
            name=Loc(key='option-type'),
            description=Loc(key='clan-warlog-type-description'),
            choices=[
                Loc('War Log', key='warlog'),
                Loc('CWL History', key='cwl-history'),
            ],
        ),
        limit: int = commands.Param(
            name=Loc(key='option-limit'),
            description=Loc(key='limit-description'),
            default=25,
            min_value=1,
            max_value=25,
        ),
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        if option == 'War Log':
            embed = await war_log(
                bot=self.bot,
                clan=clan,
                limit=limit,
                embed_color=embed_color,
                locale=locale,
            )
            buttons = button_generator(button_id=f'clanwarlog:{clan.tag}:{limit}', bot=self.bot)
        elif option == 'CWL History':
            embed = await cwl_performance(
                bot=self.bot,
                clan=clan,
                limit=limit,
                embed_color=embed_color,
                locale=locale,
            )
            buttons = button_generator(button_id=f'clancwlperf:{clan.tag}', bot=self.bot)
        await ctx.edit_original_message(embed=embed, components=[buttons])

    @clan.sub_command(name='sorted', description=Loc(key='clan-sorted-description'))
    async def sorted(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan: coc.Clan = options.clan,
        sort_by: str = commands.Param(
            name=Loc(key='option-sort-by'),
            description=Loc(key='sort-by-description'),
            choices=[
                Loc('Player Tag', key='choice-player-tag'),
                Loc('Role', key='choice-role'),
                Loc('Townhall Level', key='choice-townhall-level'),
                Loc('Trophies', key='choice-trophies'),
                Loc('Versus Trophies', key='choice-versus-trophies'),
                Loc('Clan Capital Contributions', key='choice-capital-contributions'),
                Loc('Clan Capital Raided', key='choice-capital-raided'),
                Loc('XP Level', key='choice-xp-level'),
                Loc('Combined Heroes', key='choice-combined-heroes'),
                Loc('Obstacles Removed', key='choice-obstacles-removed'),
                Loc('War Stars', key='choice-war-stars'),
                Loc('CWL Stars', key='choice-cwl-stars'),
                Loc('DE Looted', key='choice-de-looted'),
                Loc('Attacks Won (all time)', key='choice-attacks-won-all-time'),
                Loc('Attacks Won (season)', key='choice-attacks-won-season'),
                Loc('Defenses Won (season)', key='choice-defenses-won-season'),
                Loc('Defenses Won (all time)', key='choice-defenses-won-all-time'),
                Loc('Total Donated', key='choice-total-donated'),
                Loc('Versus Trophy Record', key='choice-versus-trophy-record'),
                Loc('Trophy Record', key='choice-trophy-record'),
                Loc('Clan Games Points', key='choice-clan-games-points'),
                Loc('Best Legend Finish', key='choice-best-legend-finish'),
            ],
        ),
        townhall: int = commands.Param(
            name=Loc(key='option-townhall'),
            description=Loc(key='townhall-description'),
            default=None,
        ),
        limit: int = commands.Param(
            name=Loc(key='option-limit'),
            description=Loc(key='limit-description'),
            default=50,
            min_value=1,
            max_value=50,
        ),
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        embed = await clan_sorted(
            bot=self.bot,
            clan=clan,
            sort_by=sort_by,
            townhall=townhall,
            limit=limit,
            embed_color=embed_color,
            locale=locale,
        )

        buttons = button_generator(button_id=f'clansorted:{clan.tag}:{sort_by}:{limit}:{townhall}', bot=self.bot)

        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(
        name='summary',
        description=Loc(key='clan-summary-description'),
    )
    async def summary(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan=options.clan,
        season: str = options.optional_season,
        limit: int = commands.Param(default=5, min_value=1, max_value=50),
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        embeds = await clan_summary(
            bot=self.bot,
            clan=clan,
            limit=limit,
            season=season,
            embed_color=embed_color,
            locale=locale,
        )

        buttons = button_generator(button_id=f'clansummary:{clan.tag}:{season}:{limit}', bot=self.bot)

        await ctx.edit_original_message(embeds=embeds, components=buttons)


def setup(bot):
    bot.add_cog(ClanCommands(bot))
