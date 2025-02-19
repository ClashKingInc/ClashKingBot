import disnake
from disnake.ext import commands

from discord import autocomplete, options, convert
import coc
from classes.bot import CustomClient
from .embeds import clan_composition, detailed_clan_board


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
            name='type',
            default=Loc('Townhall', key="townhall"),
            choices=[
                Loc('Townhall', key="townhall"),
                Loc('Trophies', key="trophies"),
                Loc('Location', key="location"),
                Loc('Role', key="role"),
                Loc('League', key="league"),
            ],
            convert_defaults=True,
            converter=convert.locale_to_string
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
        type: str = commands.Param(default='Detailed', choices=['Minimalistic', 'Basic', 'Detailed']),
    ):
        """
        Parameters
        ----------
        clan: Use clan tag or select an option from the autocomplete
        type: board type
        """
        embed_color = (await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)).embed_color
        _, locale = self.bot.get_localizator(ctx=ctx)

        if type == 'Detailed':
            custom_id = f'clandetailed:{clan.tag}'
            embed = await detailed_clan_board(bot=self.bot, clan=clan, server=ctx.guild, embed_color=embed_color, locale=locale)
        '''elif type == 'Basic':
            custom_id = f'clanbasic:{clan.tag}'
            embed = await basic_clan_board(bot=self.bot, clan=clan, embed_color=embed_color)
        elif type == 'Minimalistic':
            custom_id = f'clanmini:{clan.tag}'
            embed = await minimalistic_clan_board(bot=self.bot, clan=clan, server=ctx.guild, embed_color=embed_color)'''

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(
                label='',
                emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey,
                custom_id=custom_id,
            ),
            disnake.ui.Button(label='Open In-Game', url=clan.share_link, style=disnake.ButtonStyle.url),
        )
        await ctx.edit_original_response(embed=embed, components=[buttons])




def setup(bot):
    bot.add_cog(ClanCommands(bot))
