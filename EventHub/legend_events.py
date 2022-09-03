from disnake.ext import commands
import disnake

from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import player_ee
from CustomClasses.CustomPlayer import MyCustomPlayer

class LegendEvents(commands.Cog, name="Clan Capital Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("trophies", self.legend_event)

    async def legend_event(self, event):
        try:
            clan_tag = event["new_player"]["clan"]["tag"]
        except:
            return
        player_tag = event["new_player"]["tag"]
        player: MyCustomPlayer = await self.bot.getPlayer(player_tag=player_tag, custom=True)



def setup(bot: CustomClient):
    bot.add_cog(LegendEvents(bot))