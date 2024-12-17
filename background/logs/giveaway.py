from datetime import datetime, timezone
from random import choices

import disnake
from disnake.ext import commands

from background.logs.events import giveaway_ee
from utility.search import search_results


class GiveawayEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        giveaway_ee.on('giveaway_start', self.on_giveaway_start)
        giveaway_ee.on('giveaway_end', self.on_giveaway_end)

    async def get_user_roles(self, guild_id, user_id: str) -> list:
        """
        Get the roles of a user in a guild.

        Args:
            user_id (str): L'ID de l'utilisateur.

        Returns:
            list: List of role IDs the user has.
        """
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return []

        # Fetch the member object
        try:
            member = await guild.fetch_member(int(user_id))
            if member:
                # Return the role IDs (excluding @everyone)
                return [str(role.id) for role in member.roles if role.name != "@everyone"]
        except Exception as e:
            print(f"Error fetching user roles: {e}")

        return []

    async def on_giveaway_start(self, data):
        """
        Handle the 'giveaway_start' event and add a "Participate" button with an image.
        """
        # Extract giveaway data
        channel_id = data['channel_id']
        prize = data['prize']
        mentions = data.get('mentions', [])
        text_in_embed = data.get("text_in_embed", "")
        text_above_embed = data.get("text_above_embed", "")
        image_url = data.get("image_url", None)  # Optional image
        end_time = data.get("end_time")  # UNIX timestamp
        giveaway_id = data.get('giveaway_id', 'unknown')  # Giveaway ID (fallback if missing)
        winners_count = data.get('winners_count', 1)

        # Dynamic plural handling for winners count
        winners_text = "Winner" if winners_count == 1 else "Winners"

        # Convert end_time to a readable format
        if end_time:
            end_datetime = datetime.fromtimestamp(end_time, tz=timezone.utc)
            formatted_end_time = end_datetime.strftime("%a %d %b %Y at %H:%M UTC")
            footer_text = f"Ends on {formatted_end_time}"
        else:
            footer_text = "End time not provided."

        # Embed for giveaway start
        embed = disnake.Embed(
            title=f"🎉 {prize} - {winners_count} {winners_text} 🎉",
            description=f"{text_in_embed}",
            color=disnake.Color.blurple(),
            timestamp=datetime.now(timezone.utc)  # Adds the current time
        )
        embed.add_field(name="🎟️ How to Enter", value="Click the **Participate** button below!", inline=False)

        # Add image if provided
        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text=footer_text)

        # "Participate" button
        participate_button = disnake.ui.Button(
            label="🎟️ Participate (0)",  # Show 0 participants initially
            style=disnake.ButtonStyle.blurple,
            custom_id=f"giveaway_{giveaway_id}"
        )
        components = [disnake.ui.ActionRow(participate_button)]

        # Generate the mention text
        mention_text = " ".join([f"<@&{mention}>" for mention in mentions]) if mentions else ""

        # Send the embed to the channel
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            # Combine mention_text and text_above_embed, ensuring proper spacing
            content = f"{mention_text}\n{text_above_embed}".strip() if mention_text or text_above_embed else None

            if content:
                message = await channel.send(content=content, embed=embed, components=components)
            else:
                message = await channel.send(embed=embed, components=components)

            # Save the message ID in the database for later updates
            await self.bot.giveaways.update_one(
                {"_id": giveaway_id},
                {"$set": {"message_id": message.id}}
            )
            print(f"Sent giveaway start message to channel {channel_id}")

    async def on_giveaway_end(self, data):
        """
        Handle the 'giveaway_end' event and display winners/participants.
        """
        # Extract giveaway data
        participants = data.get('participants', [])
        winner_count = data.get('winner_count', 0)
        channel_id = data['channel_id']
        prize = data['prize']
        winners_count = data.get('winners_count', 1)
        text_on_end = data.get("text_on_end", "")
        boosters = data.get('boosters', [])
        guild_id = data.get('server_id', 'unknown')

        weights = []
        for participant in participants:
            user_roles = await self.get_user_roles(guild_id, participant)

            # Find applicable boosters for the user
            applicable_boosts = [booster["value"] for booster in boosters if
                                 any(role in booster["roles"] for role in user_roles)]

            if applicable_boosts:
                # If boosters are found, set the weight to the highest value
                weight = max(applicable_boosts)
            else:
                # If no boosters are found, set the weight to 1
                weight = 1

            weights.append(weight)

        # Determine if there's one or multiple winners
        winners_text = "Winner" if winners_count == 1 else "Winners"

        # Determine winners
        winners = []
        if participants and winner_count > 0:
            winners = choices(participants, weights=weights, k=min(winner_count, len(participants)))

        # Format mention text for winners
        mention_text = ' '.join([f'<@{winner}>' for winner in winners]) if winners else "No winners"

        # Build the embed
        embed = disnake.Embed(
            title=f"🎉 {prize} - {winners_count} {winners_text} 🎉",
            description=f"**Total Participants:** {len(participants)}",
            color=disnake.Color.red(),
        )

        # Get the target channel
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            # Combine mention_text and text_on_end
            content = f"{mention_text}\n{text_on_end}".strip() if mention_text or text_on_end else None

            # Send the message
            await channel.send(content=content, embed=embed) if content else await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_button_click(self, interaction: disnake.MessageInteraction):
        """
        Listener for giveaway participation buttons.
        """
        if interaction.component.custom_id.startswith("giveaway_"):
            giveaway_id = interaction.component.custom_id.split("_")[1]

            # Fetch giveaway from the database (ID as a string)
            giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
            if not giveaway:
                await interaction.response.send_message("This giveaway no longer exists.", ephemeral=True)
                return

            # Check if the user already entered
            if str(interaction.user.id) in giveaway.get("entries", []):
                await interaction.response.send_message("You have already entered this giveaway!", ephemeral=True)
                return

            # Check for roles allow/deny rules
            user_roles = [str(role.id) for role in interaction.user.roles]
            roles_mode = giveaway.get("roles_mode", "allow")
            allowed_roles = giveaway.get("roles", [])

            if roles_mode == "deny" and any(role in allowed_roles for role in user_roles) is False:
                await interaction.response.send_message("You are not allowed to enter this giveaway.", ephemeral=True)
                return
            elif roles_mode == "allow" and any(role in allowed_roles for role in user_roles):
                await interaction.response.send_message("You are not allowed to enter this giveaway.", ephemeral=True)
                return

            # Check profile picture requirement
            if giveaway.get("profile_picture_required") and interaction.user.avatar is None:
                await interaction.response.send_message("You need a profile picture to enter this giveaway.",
                                                        ephemeral=True)
                return

            # Check Clash account requirement
            if giveaway.get("coc_account_required"):
                search_query = str(interaction.user.id)
                results = await search_results(self.bot, search_query)
                if not results:
                    await interaction.response.send_message(
                        "You need a linked Clash account to enter this giveaway.",
                        ephemeral=True)
                    return

            # Update entries in the database
            await self.bot.giveaways.update_one(
                {"_id": giveaway_id},
                {"$push": {"entries": str(interaction.user.id)}}
            )

            # Fetch updated giveaway data
            updated_giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
            new_participants_count = len(updated_giveaway.get("entries", []))

            # Update the message with the new participant count
            channel = interaction.channel
            try:
                message = await channel.fetch_message(giveaway["message_id"])
                updated_button = disnake.ui.Button(
                    label=f"🎟️ Participate ({new_participants_count})",
                    style=disnake.ButtonStyle.blurple,
                    custom_id=f"giveaway_{giveaway_id}"
                )
                components = [disnake.ui.ActionRow(updated_button)]

                await message.edit(components=components)
                await interaction.response.send_message("You successfully joined the giveaway! 🎉", ephemeral=True)
            except disnake.NotFound:
                await interaction.response.send_message("The giveaway message could not be found.", ephemeral=True)


def setup(bot):
    bot.add_cog(GiveawayEvents(bot))
