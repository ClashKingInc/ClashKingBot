
import disnake
import inspect

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utility.discord_utils import registered_functions


class ButtonHandler(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        button_data = ctx.data.custom_id
        if ":" not in button_data:
            return

        split_data = button_data.split(":")
        lookup_name = button_data.split(":")[0]
        function, parser, ephemeral, no_embed = registered_functions.get(lookup_name)
        await ctx.response.defer(ephemeral=ephemeral)


        parser_split = parser.split(":")

        hold_kwargs = {"bot" : self.bot, "server" : ctx.guild}
        for data, name in zip(split_data[1:], parser_split[1:]):
            if data.isdigit():
                data = int(data)
            if name == "server":
                if data == ctx.guild_id:
                    continue
                else:
                    data = await self.bot.getch_guild(data)

            if data == "None":
                data = None
            if name == "clan":
                data = await self.bot.getClan(clan_tag=data)
            if name == "ctx":
                data = ctx
            hold_kwargs[name] = data

        server = hold_kwargs.get("server")
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=server.id)
        hold_kwargs["embed_color"] = embed_color
        hold_kwargs = {key: hold_kwargs[key] for key in inspect.getfullargspec(function).args}
        embed = await function(**hold_kwargs)

        #in some cases the handling is done outside this function
        if no_embed:
            return

        if isinstance(embed, list):
            await ctx.edit_original_message(embeds=embed)
        else:
            await ctx.edit_original_message(embed=embed)

def setup(bot):
    bot.add_cog(ButtonHandler(bot))


