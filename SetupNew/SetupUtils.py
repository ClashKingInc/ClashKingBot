import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from typing import Callable
from Exceptions.Exceptions import ExpiredComponents

class SetupUtils(commands.Cog, name="SetupUtils"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def interaction_handler(self, ctx: disnake.ApplicationCommandInteraction, function: Callable = None, no_defer = False):
        async def return_res(res):
            return res

        if function is None:
            function = return_res

        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        valid_value = None
        while valid_value is None:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                raise ExpiredComponents

            if res.author.id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", ephemeral=True)
                continue

            if not no_defer:
                await res.response.defer()
            valid_value = await function(res=res)

        return valid_value


