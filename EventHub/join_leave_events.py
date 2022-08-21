from disnake.ext import commands
import disnake

from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import clan_ee


class join_leave_events(commands.Cog, name="Clan Join & Leave Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @clan_ee.on("memberList")
    async def join_leave_events(self, event):
        return print(event)


def setup(bot: CustomClient):
    bot.add_cog(join_leave_events(bot))