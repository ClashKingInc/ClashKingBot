import disnake
import inspect

from disnake.ext import commands
from classes.bot import CustomClient
from utility.discord_utils import registered_functions


async def button_logic(
    button_data: str,
    bot: CustomClient,
    guild: disnake.Guild,
    ctx: disnake.MessageInteraction = None,
):
    split_data = button_data.split(":")
    lookup_name = button_data.split(":")[0]
    # print(registered_functions.keys())
    function, parser, ephemeral, no_embed = registered_functions.get(lookup_name)
    if function is None:
        return None, 0  # maybe change this
    if ctx:
        await ctx.response.defer(ephemeral=ephemeral)

    parser_split = parser.split(":")
    hold_kwargs = {"bot": bot, "server": guild}
    for data, name in zip(split_data[1:], parser_split[1:]):
        if data.isdigit():
            data = int(data)
        if name == "server":
            if data == guild.id:
                continue
            else:
                data = await bot.getch_guild(data)
        if data == "None":
            data = None
        if name == "clan":
            data = await bot.getClan(clan_tag=data)
        elif name == "ctx":
            data = ctx
        elif name == "player":
            data = await bot.getPlayer(player_tag=data)
        elif name == "custom_player":
            data = await bot.getPlayer(player_tag=data, custom=True)
        elif name == "discord_user":
            data = await ctx.guild.getch_member(data)
        hold_kwargs[name] = data

    embed_color = await bot.ck_client.get_server_embed_color(server_id=guild.id)
    hold_kwargs["embed_color"] = embed_color
    hold_kwargs = {key: hold_kwargs[key] for key in inspect.getfullargspec(function).args}
    embed = await function(**hold_kwargs)

    components = 0
    components_function = None
    if components_function:
        hold_kwargs["ctx"] = ctx
        components = await components_function(**hold_kwargs)

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

        if ":" not in button_data:
            return

        embed, components = await button_logic(button_data=button_data, bot=self.bot, ctx=ctx, guild=ctx.guild)

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
                await ctx.edit_original_message(embed=embed)


def setup(bot):
    bot.add_cog(ComponentHandler(bot))
