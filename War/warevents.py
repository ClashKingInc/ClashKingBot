import coc
import discord
from HelperMethods.clashClient import client, coc_client, getPlayer

usafam = client.usafam
server = usafam.server
clans = usafam.clans
war = usafam.war

from discord.ext import commands

class WarEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.war_spin)

    @coc.WarEvents.state()
    async def war_spin(self, old_war, new_war):
        end_time = new_war.end_time.time



def setup(bot: commands.Bot):
    bot.add_cog(WarEvents(bot))