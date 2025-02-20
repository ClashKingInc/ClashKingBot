import disnake
from disnake.ext import commands

from discord import autocomplete, options, convert
import coc
from classes.bot import CustomClient
from .embeds import clan_composition, detailed_clan_board, basic_clan_board, minimalistic_clan_board, clan_donations


from disnake import Localized as Loc

from utility.discord.components import button_generator

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
        name='compo',
        description = Loc(key='clan-compo-description'),
        extras = {'docs': 'https://docs.clashking.xyz/clan-and-family-commands/clan-commands#clan-compo-clan-type'},
    )
    async def compo(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan = options.clan,
        type_: str = commands.Param(
            description=Loc(key='clan-compo-type-description'),
            name=Loc(key='option-type'),
            default='Townhall',
            choices=[
                Loc('Townhall', key="townhall"),
                Loc('Trophies', key="trophies"),
                Loc('Location', key="location"),
                Loc('Role', key="role"),
                Loc('League', key="league"),
            ],
        )
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        embed = await clan_composition(
            bot=self.bot,
            clan=clan,
            type=type_,
            embed_color=embed_color,
            locale=locale,
        )
        buttons = button_generator(button_id=f'clancompo:{clan.tag}:{type_}', bot=self.bot)
        await ctx.edit_original_response(embed=embed, components=buttons)



    @clan.sub_command(
        name='search',
        description=Loc(key='clan-search-description'),
    )
    async def search(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        clan = options.clan,
        type_: str = commands.Param(
            name=Loc(key='option-type'),
            description=Loc(key='clan-search-type-description'),
            default='Detailed',
            choices=[
                Loc('Minimalistic', key="minimalistic"),
                Loc('Basic', key="basic"),
                Loc('Detailed', key="detailed"),
            ],
        ),
    ):
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        if type_ == 'Detailed':
            custom_id = f'clandetailed:{clan.tag}'
            embed = await detailed_clan_board(bot=self.bot, clan=clan, server=ctx.guild, embed_color=embed_color, locale=locale)
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
            disnake.ui.Button(label=_("open-in-game"), url=clan.share_link, style=disnake.ButtonStyle.url),
        ]
        await ctx.edit_original_response(embed=embed, components=[buttons])




    @clan.sub_command(
        name='donations',
        description='Donation stats for a clan'
    )
    async def donations(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            clan = options.clan,
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
                default="Donations",
                choices=[
                    Loc('Name', key='name'),
                    Loc('Townhall', key='townhall' ),
                    Loc('Donations', key='donations' ),
                    Loc('Received', key='received' ),
                    Loc('Ratio', key='ratio')
                ],
            ),
            sort_order: str = commands.Param(
                name=Loc(key='option-sort-order'),
                description=Loc(key='sort-order-description'),
                default='Descending',
                choices=[
                    Loc('Ascending', key="ascending"),
                    Loc('Descending', key="descending")
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

        buttons = button_generator(
            button_id=f'clandonos:{clan.tag}:{season}:{townhall}:{limit}:{sort_by}:{sort_order}',
            bot=self.bot
        )
        await ctx.edit_original_message(embed=embed, components=[buttons])


def setup(bot):
    bot.add_cog(ClanCommands(bot))
