import disnake
from disnake.ext import commands
from bson.objectid import ObjectId  # For MongoDB ID handling


class GiveawayClickHandler(commands.Cog):
    """
    Handles interactions for giveaway buttons.
    """
    def __init__(self, bot):
        self.bot = bot
        print("GiveawayClickHandler cog has been loaded!")

    @commands.Cog.listener()
    async def on_button_click(self, interaction: disnake.MessageInteraction):
        # Check if the button is for a giveaway
        print(f"Button clicked: {interaction.component.custom_id}")
        if interaction.component.custom_id.startswith("giveaway_"):
            giveaway_id = interaction.component.custom_id.split("_")[1]

            # Validate the giveaway ID
            try:
                giveaway_id = ObjectId(giveaway_id)
            except Exception:
                await interaction.response.send_message("Invalid giveaway ID.", ephemeral=True)
                return

            # Fetch the giveaway details from the database
            giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
            if not giveaway:
                await interaction.response.send_message("This giveaway no longer exists.", ephemeral=True)
                return

            # Check if the user has already entered
            if interaction.user.id in giveaway["entries"]:
                await interaction.response.send_message("You have already entered this giveaway!", ephemeral=True)
                return

            # Add the user to the giveaway entries
            await self.bot.giveaways.update_one(
                {"_id": giveaway_id},
                {"$push": {"entries": interaction.user.id}}
            )

            # Confirm their entry
            await interaction.response.send_message("You have successfully entered the giveaway! 🎉", ephemeral=True)


def setup(bot):
    """
    Adds the GiveawayClickHandler to the bot.
    """
    bot.add_cog(GiveawayClickHandler(bot))
