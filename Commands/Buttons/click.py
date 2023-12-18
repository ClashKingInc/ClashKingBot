
import disnake

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Utils.constants import EMBED_COLOR
from .converter import get_function

class CommandButtons(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if ctx.data.custom_id.startswith("clan_") or ctx.data.custom_id.startswith("family_"):
            result = await self.bot.button_store.find_one({"button_id": ctx.data.custom_id})
            if result is None:
                return await ctx.send(content="**No action tied to this button, try rerunning this command**", ephemeral=True)

            await ctx.response.defer()

            server_result = await self.bot.server_db.find_one({"server": ctx.guild_id})
            hold_kwargs = {"embed_color" : disnake.Color(server_result.get("embed_color", EMBED_COLOR)), "bot" : self.bot}
            for field in result.get("fields"):
                field_result = result.get(field)
                if field == "clan":
                    field_result = await self.bot.getClan(clan_tag=field_result)
                elif field == "server":
                    field_result = await self.bot.getch_guild(guild_id=field_result)
                hold_kwargs[field] = field_result

            embed = await get_function(name=result.get("command"))(**hold_kwargs)



            if isinstance(embed, list):
                await ctx.edit_original_message(embeds=embed)
            else:
                await ctx.edit_original_message(embed=embed)


def setup(bot):
    bot.add_cog(CommandButtons(bot))
