
import disnake
import time

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from BoardCommands.Buttons.ButtonSwitcher import button_click_to_embed


class Buttons(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        embed, send = await button_click_to_embed(bot=self.bot, ctx=ctx)
        if embed is not None:
            if isinstance(embed, list):
                if send:
                    await ctx.send(embeds=embed, ephemeral=True)
                else:
                    await ctx.edit_original_message(embeds=embed)
            elif isinstance(embed, str):
                await ctx.edit_original_message(content=embed)
            else:
                if send:
                    await ctx.send(embed=embed, ephemeral=True)
                else:
                    await ctx.edit_original_message(embed=embed)



def setup(bot):
    bot.add_cog(Buttons(bot))

