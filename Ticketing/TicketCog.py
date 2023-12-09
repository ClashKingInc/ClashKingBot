from disnake.ext import commands
from Ticketing import TicketCommands
from Ticketing import TicketClick

class TicketCog(TicketCommands.TicketCommands, TicketClick.TicketClick, commands.Cog, name="Ticket Commands"):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot


def setup(bot):
    bot.add_cog(TicketCog(bot))
