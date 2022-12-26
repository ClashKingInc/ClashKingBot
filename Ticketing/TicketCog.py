from disnake.ext import commands
from Ticketing import TicketCommands, TicketButtons


class TicketCog(TicketCommands.TicketCommands, commands.Cog, name="Ticket Commands"):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot


def setup(bot):
    bot.add_cog(TicketCog(bot))
