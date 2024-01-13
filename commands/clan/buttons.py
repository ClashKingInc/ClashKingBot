
import disnake
import inspect

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utility.discord_utils import registered_functions


class ClanButtons(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if not ctx.data.custom_id.startswith("clan"):
            return

        '''types
        - clandetailed, _:clan
        '''
        await ctx.response.defer()

        button_data = ctx.data.custom_id
        lookup_name = button_data.split(":")[0]
        function, parser = registered_functions.get(lookup_name)
        split_data = button_data.split(":")
        parser_split = parser.split(":")

        hold_kwargs = {"bot" : self.bot, "server" : ctx.guild}
        for data, name in zip(split_data[1:], parser_split[1:]):
            if data == "None":
                data = None
            if name == "clan":
                data = await self.bot.getClan(clan_tag=data)
            hold_kwargs[name] = data

        server = hold_kwargs.get("server")
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=server.id)
        hold_kwargs["embed_color"] = embed_color
        hold_kwargs = {key: hold_kwargs[key] for key in inspect.getfullargspec(function).args}

        embed = await function(**hold_kwargs)

        if isinstance(embed, list):
            await ctx.edit_original_message(embeds=embed)
        else:
            await ctx.edit_original_message(embed=embed)




