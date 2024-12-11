import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
from bson.objectid import ObjectId  # For MongoDB ID generation

from .click import GiveawayClickHandler


class GiveawayCommands(GiveawayClickHandler, commands.Cog):
    """
    Handles slash commands for giveaways.
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="giveaway", description="Manage giveaways in the server")
    async def giveaway(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Parent command for giveaways. Only serves as a container for subcommands.
        """
        pass

    @giveaway.sub_command(
        name="create",
        description="Create a new giveaway"
    )
    async def create_giveaway(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        prize: str = commands.Param(description="Prize for the giveaway"),
        duration: int = commands.Param(description="Duration in minutes"),
        winners: int = commands.Param(description="Number of winners"),
        channel: disnake.TextChannel = commands.Param(description="Channel to post the giveaway")
    ):
        """
        Create a new giveaway.
        Parameters:
        - prize: The reward for the giveaway.
        - duration: How long the giveaway will last (in minutes).
        - winners: Number of winners.
        - channel: The text channel to post the giveaway.
        """
        await ctx.response.defer(ephemeral=True)

        # Generate a unique ID for the giveaway
        giveaway_id = ObjectId()

        # Calculate the giveaway's end time
        end_time = datetime.utcnow() + timedelta(minutes=duration)

        # Create the giveaway embed
        embed = disnake.Embed(
            title="🎉 New Giveaway 🎉",
            description=(
                f"**Prize**: {prize}\n"
                f"**Number of winners**: {winners}\n"
                f"**Ends at**: <t:{int(end_time.timestamp())}:F>"
            ),
            color=disnake.Color.green()
        )
        embed.set_footer(text=f"Organized by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

        # Add a participation button
        button = disnake.ui.Button(
            label="Enter Giveaway 🎟️",
            style=disnake.ButtonStyle.green,
            custom_id=f"giveaway_{giveaway_id}"
        )
        message = await channel.send(embed=embed, components=[disnake.ui.ActionRow(button)])

        # Save giveaway details in the database
        giveaway_data = {
            "_id": giveaway_id,
            "server": ctx.guild_id,
            "prize": prize,
            "end_time": end_time,
            "winners": winners,
            "channel_id": channel.id,
            "message_id": message.id,
            "entries": []  # List of participant IDs
        }
        await self.bot.giveaways.insert_one(giveaway_data)

        # Confirm to the user that the giveaway was created
        await ctx.send(f"Giveaway successfully created in {channel.mention}!", ephemeral=True)


def setup(bot):
    """
    Adds the GiveawayCommands cog to the bot.
    """
    bot.add_cog(GiveawayCommands(bot))