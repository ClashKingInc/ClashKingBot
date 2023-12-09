import coc
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands

class Example(commands.Cog, name="ExampleCog"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.coc_client.add_events(self.foo)

    @coc.ClanEvents.member_join()
    async def foo(self, member, clan):
        pass

def setup(bot: CustomClient):
    bot.add_cog(Example(bot))