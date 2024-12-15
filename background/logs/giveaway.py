import disnake
from disnake.ext import commands
from background.logs.events import giveaway_ee

class GiveawayEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        giveaway_ee.on('giveaway_start', self.on_giveaway_start)
        giveaway_ee.on('giveaway_end', self.on_giveaway_end)

    async def on_giveaway_start(self, data):
        """
        Handle the 'giveaway_start' event.
        """
        channel_id = data['channel_id']
        prize = data['prize']
        mentions = data['mentions']
        embed = disnake.Embed(
            title="🎉 Giveaway Started!",
            description=f"Prize: **{prize}**\n{' '.join(mentions)}",
            color=disnake.Color.green()
        )
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            await channel.send(embed=embed)

    async def on_giveaway_end(self, data):
        """
        Handle the 'giveaway_end' event.
        """
        channel_id = data['channel_id']
        prize = data['prize']
        winner_count = data.get('winner_count', 0)
        embed = disnake.Embed(
            title="🎉 Giveaway Ended!",
            description=f"Prize: **{prize}**\nWinners: **{winner_count}**",
            color=disnake.Color.red()
        )
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(GiveawayEvents(bot))