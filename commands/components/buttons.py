import inspect

import disnake
from disnake.ext import commands

from classes.bot import CustomClient
from utility.components import button_generator
from utility.discord_utils import registered_functions
import pendulum as pend

async def button_logic(
    button_data: str,
    bot: CustomClient,
    guild: disnake.Guild,
    locale: disnake.Locale,
    ctx: disnake.MessageInteraction | None = None,
    autoboard: bool = False,
):
    split_data = button_data.split(':')
    lookup_name = button_data.split(':')[0]

    function, parser, ephemeral, no_embed, pagination = registered_functions.get(lookup_name, (None, '', False, False, False))

    if function is None:
        return None, 0  # maybe change this
    if ctx:
        await ctx.response.defer(ephemeral=ephemeral)

    page = 0
    if pagination and 'page=' in split_data[-1]:
        page = int(split_data.pop(-1).replace('page=', ''))

    if ctx is not None and not autoboard and pagination and ctx.author.id != ctx.message.interaction.author.id and page != -1:
        await ctx.send('Must run the command to interact with pagination', ephemeral=True)
        return None, 0

    page = max(page, 0)

    parser_split = parser.split(':')
    hold_kwargs = {'bot': bot, 'server': guild, 'locale': locale}
    for data, name in zip(split_data[1:], parser_split[1:]):
        if data.isdigit():
            data = int(data)
        if name == 'server':
            if data == guild.id:
                continue
            else:
                data = await bot.getch_guild(data)
        if data == 'None':
            data = None
        if name == 'clan':
            data = await bot.getClan(clan_tag=data)
        elif name == 'ctx':
            data = ctx
        elif name == 'player':
            data = await bot.getPlayer(player_tag=data)
        elif name == 'custom_player':
            data = await bot.getPlayer(player_tag=data, custom=True)
        elif name == 'discord_user':
            ctx: disnake.ApplicationCommandInteraction
            if ctx.guild:
                data = await ctx.guild.getch_member(data)
            else:
                data = ctx.user
        hold_kwargs[name] = data

    embed_color = await bot.ck_client.get_server_embed_color(server_id=None if not guild else guild.id)
    hold_kwargs['embed_color'] = embed_color
    # Ensure function signature respects wrapped functions
    signature = inspect.signature(function)
    valid_keys = list(signature.parameters.keys())

    # Keep only valid keys
    hold_kwargs = {key: hold_kwargs[key] for key in valid_keys if key in hold_kwargs}
    embed = await function(**hold_kwargs)

    components = 0
    if pagination and isinstance(embed, list):
        components = button_generator(button_id=':'.join(split_data), current_page=page, max_page=len(embed), bot=bot)
        embed = embed[min(len(embed) - 1, page)]

    if isinstance(embed, disnake.Embed):
        embed.timestamp = pend.now(tz=pend.UTC)

    if no_embed:
        return None, 0
    return embed, components


class ComponentHandler(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_interaction(self, ctx: disnake.MessageInteraction):

        if ctx.data.component_type == disnake.ComponentType.button:
            button_data = ctx.data.custom_id
        elif ctx.data.component_type == disnake.ComponentType.select:
            button_data = ctx.values[0]
        else:
            return

        if ':' not in button_data:
            return

        locale = self.bot.get_locale(ctx=ctx)
        embed, components = await button_logic(
            button_data=button_data,
            bot=self.bot,
            ctx=ctx,
            guild=ctx.guild,
            locale=locale,
        )

        # in some cases the handling is done outside this function
        if embed is None:
            return

        if isinstance(embed, list):
            if components != 0:
                await ctx.edit_original_message(embeds=embed, components=components)
            else:
                await ctx.edit_original_message(embeds=embed)
        else:
            if components != 0:
                await ctx.edit_original_message(embed=embed, components=components)
            else:
                await ctx.edit_original_message(embed=embed, attachments=[])


def setup(bot):
    bot.add_cog(ComponentHandler(bot))
