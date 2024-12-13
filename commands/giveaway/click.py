import disnake
from disnake.ext import commands
from bson.objectid import ObjectId  # For MongoDB ID handling

from utility.search import search_results


class GiveawayClickHandler(commands.Cog):
    """
    Handles interactions for giveaway buttons.
    """

    def __init__(self, bot):
        self.bot = bot
        print("GiveawayClickHandler cog has been loaded!")

    @commands.Cog.listener()
    async def on_button_click(self, interaction: disnake.MessageInteraction):
        """
        Listener for giveaway participation buttons.
        """
        if interaction.component.custom_id.startswith("giveaway_"):
            giveaway_id = interaction.component.custom_id.split("_")[1]

            # Validate the giveaway ID as an ObjectId
            try:
                giveaway_id = ObjectId(giveaway_id)
            except Exception:
                await interaction.response.send_message("Invalid giveaway ID.", ephemeral=True)
                return

            # Retrieve the giveaway details from the database
            giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})

            if not giveaway:
                await interaction.response.send_message("This giveaway no longer exists.", ephemeral=True)
                return

            # Retrieve options
            options = giveaway.get("options", {})
            require_profile_pic = options.get("require_profile_pic", False)
            require_clash_account = options.get("require_clash_account", False)

            # Check profile picture requirement
            if require_profile_pic and interaction.user.avatar is None:
                await interaction.response.send_message("You need a profile picture to enter this giveaway.",
                                                        ephemeral=True)
                return

            # Check Clash account requirement
            if require_clash_account:
                search_query = str(interaction.user.id)
                results = await search_results(self.bot, search_query)
                if not results:
                    await interaction.response.send_message("You need a linked Clash account to enter this giveaway.",
                                                            ephemeral=True)
                    return

            # Check if the user has already entered
            if interaction.user.id in giveaway["entries"]:
                await interaction.response.send_message("You have already entered this giveaway!", ephemeral=True)
                return

            # Add the user to the entries list in the database
            await self.bot.giveaways.update_one(
                {"_id": giveaway_id},
                {"$push": {"entries": interaction.user.id}}
            )

            # Update the number of participants
            updated_giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
            participant_count = len(updated_giveaway["entries"])

            # Retrieve the original message
            channel = interaction.guild.get_channel(giveaway["channel_id"])
            if not channel:
                await interaction.response.send_message("Failed to retrieve the giveaway channel.", ephemeral=True)
                return
            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except disnake.NotFound:
                await interaction.response.send_message("The giveaway message could not be found.", ephemeral=True)
                return

            # Update the embed with the new participant count
            embed = message.embeds[0]
            embed.description += f"\n**Participants**: {participant_count}"

            # Disable the button for this user
            new_button = disnake.ui.Button(
                label="Already Entered 🎟️",
                style=disnake.ButtonStyle.grey,
                disabled=True,
                custom_id=interaction.component.custom_id
            )
            components = [disnake.ui.ActionRow(new_button)]

            await message.edit(embed=embed, components=components)
            await interaction.response.send_message("You have successfully entered the giveaway! 🎉", ephemeral=True)

def setup(bot):
    """
    Adds the GiveawayClickHandler to the bot.
    """
    bot.add_cog(GiveawayClickHandler(bot))
