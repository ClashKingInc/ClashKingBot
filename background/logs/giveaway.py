from datetime import datetime, timezone
from random import choices

import disnake
from disnake.ext import commands

from background.logs.events import giveaway_ee
import pendulum as pend
from classes.bot import CustomClient
from pymongo import ReturnDocument


class GiveawayEvents(commands.Cog, name="Giveaway Events"):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        giveaway_ee.on('giveaway_start', self.on_giveaway_start)
        giveaway_ee.on('giveaway_end', self.on_giveaway_end)
        giveaway_ee.on('giveaway_update', self.on_giveaway_update)

    async def update_button(self, giveaway_id: str, message: disnake.Message):
        try:
            giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
            participants_count = len(giveaway.get("entries", []))

            updated_button = disnake.ui.Button(
                label=f"🎟️ Participate ({participants_count})",
                style=disnake.ButtonStyle.blurple,
                custom_id=f"giveaway_{giveaway_id}"
            )
            components = [disnake.ui.ActionRow(updated_button)]
            await message.edit(components=components)
        except Exception:
            pass


    async def get_user_roles(self, guild_id: int, user_id: str) -> list:
        """
        Get the roles of a user in a guild.

        Args:
            user_id (str): The user ID to fetch roles for.

        Returns:
            list: List of role IDs the user has.
        """
        guild = await self.bot.getch_guild(guild_id)
        if guild is None:
            return []

        if not guild.chunked:
            if guild.id not in self.bot.STARTED_CHUNK:
                await guild.chunk(cache=True)
            else:
                self.bot.STARTED_CHUNK.add(guild.id)

        try:
            member = await guild.getch_member(int(user_id))
            if member:
                # Return the role IDs (excluding @everyone)
                return [str(role.id) for role in member.roles if role.name != "@everyone"]
        except Exception as e:
            print(f"Error fetching user roles: {e}")

        return []

    async def on_giveaway_start(self, data: dict):
        """
        Handle the 'giveaway_start' event and add a "Participate" button with an image.
        """
        # Extract giveaway data
        giveaway = data['giveaway']
        server_id = giveaway.get('server_id', 'unknown')
        if server_id not in self.bot.OUR_GUILDS:
            return
        channel_id = giveaway['channel_id']
        prize = giveaway['prize']
        mentions = giveaway.get('mentions', [])
        text_in_embed = giveaway.get("text_in_embed", "")
        text_above_embed = giveaway.get("text_above_embed", "")
        image_url = giveaway.get("image_url", None)  # Optional image
        end_time = giveaway.get("end_time")  # ISO 8601 string
        giveaway_id = giveaway.get('_id', 'unknown')  # Giveaway ID
        winners_count = giveaway.get('winners', 1)

        # Dynamic plural handling for winners count
        winners_text = "Winner" if winners_count == 1 else "Winners"

        # Embed for giveaway start
        embed = disnake.Embed(
            title=f"🎉 {prize} - {winners_count} {winners_text} 🎉",
            description=f"{text_in_embed}",
            color=disnake.Color.blurple(),
            timestamp=pend.parse(end_time, tz='UTC') if end_time else pend.now("UTC")
        )
        embed.set_footer(text=f"Ends")

        # Add image if provided
        if image_url:
            embed.set_image(url=image_url)

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
        channel = await self.bot.getch_channel(int(channel_id))

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

    async def on_giveaway_update(self, data: dict):
        """
        Handle the 'giveaway_update' event and update the giveaway message.
        """
        # Extract giveaway data
        giveaway = data['giveaway']
        server_id = giveaway.get('server_id', 'unknown')
        if server_id not in self.bot.OUR_GUILDS:
            return
        channel_id = giveaway['channel_id']
        giveaway_id = giveaway.get('_id', 'unknown')
        prize = giveaway['prize']
        mentions = giveaway.get('mentions', [])
        text_in_embed = giveaway.get("text_in_embed", "")
        text_above_embed = giveaway.get("text_above_embed", "")
        image_url = giveaway.get("image_url", None)  # Optional image
        winners_count = giveaway.get('winners', 1)
        message_id = giveaway.get("message_id")

        # Check if the message ID is present
        if not message_id:
            print(f"No message ID found for giveaway {giveaway_id}.")
            return

        # Update the embed
        winners_text = "Winner" if winners_count == 1 else "Winners"
        embed = disnake.Embed(
            title=f"🎉 {prize} - {winners_count} {winners_text} 🎉",
            description=f"{text_in_embed}",
            color=disnake.Color.blurple(),
            timestamp= pend.parse(giveaway.get("end_time"), tz='UTC') if giveaway.get("end_time") else pend.now("UTC")
        )
        embed.set_footer(text=f"Ends")

        # Add image if provided
        if image_url:
            embed.set_image(url=image_url)

        # Update mentions and text above embed
        mention_text = " ".join([f"<@&{mention}>" for mention in mentions]) if mentions else ""
        content = f"{mention_text}\n{text_above_embed}".strip() if mention_text or text_above_embed else None

        # Fetch the target channel and message
        channel = await self.bot.getch_channel(int(channel_id))
        if not channel:
            print(f"Channel with ID {channel_id} not found.")
            return

        try:
            message = await channel.fetch_message(message_id)
            # Update the message content and embed
            await message.edit(content=content, embed=embed)
            print(f"Giveaway message with ID {message_id} successfully updated.")
        except disnake.NotFound:
            print(f"Message with ID {message_id} not found in channel {channel_id}.")
        except Exception as e:
            print(f"Error updating giveaway message: {e}")

    async def on_giveaway_end(self, data: dict):
        """
        Handle the 'giveaway_end' event and display winners/participants.
        """
        # Extract giveaway data
        giveaway = data['giveaway']
        server_id = giveaway.get('server_id', 'unknown')
        if server_id not in self.bot.OUR_GUILDS:
            return
        participants = giveaway.get('entries', [])
        winner_count = giveaway.get('winners', 0)
        channel_id = giveaway['channel_id']
        prize = giveaway['prize']
        winners_count = giveaway.get('winners', 1)
        text_on_end = giveaway.get("text_on_end", "")
        boosters = giveaway.get('boosters', [])
        guild_id = giveaway.get('server_id', 'unknown')
        image_url = giveaway.get("image_url", None)  # Optional image

        # Calculate weights for participants based on boosters
        weights = []
        for participant in participants:
            user_roles = await self.get_user_roles(guild_id, participant)

            # Find applicable boosters for the user
            applicable_boosts = [booster["value"] for booster in boosters if
                                 any(role in booster["roles"] for role in user_roles)]

            weight = max(applicable_boosts) if applicable_boosts else 1
            weights.append(weight)

        # Determine winners
        winners = []
        if participants and winner_count > 0:
            if len(participants) <= winner_count:
                # If there are fewer participants than winners, all participants are winners
                winners = participants
            else:
                # Use weighted random sampling to select winners
                selected_indices = set()
                while len(selected_indices) < winner_count:
                    sampled = choices(participants, weights=weights, k=1)[0]
                    if sampled not in selected_indices:
                        selected_indices.add(sampled)
                winners = list(selected_indices)

        # Format mention text for winners
        mention_text = ' '.join([f'<@{winner}>' for winner in winners]) if winners else "No winners"

        # Build the embed
        winners_text = "Winner" if winners_count == 1 else "Winners"
        embed = disnake.Embed(
            title=f"🎉 {prize} - {winners_count} {winners_text} 🎉",
            description=f"**Total Participants:** {len(participants)}",
            color=disnake.Color.red(),
        )

        # Add image if provided
        if image_url:
            embed.set_image(url=image_url)

        # Get the target channel
        channel = await self.bot.getch_channel(int(channel_id))

        if channel:
            # Combine mention_text and text_on_end
            content = f"{mention_text}\n{text_on_end}".strip() if mention_text or text_on_end else None

            # Send the message
            await channel.send(content=content, embed=embed) if content else await channel.send(embed=embed)

        # Add winners to the database
        now = pend.now("UTC")
        new_winners = [
            {
                "user_id": winner,
                "status": "winner",
                "timestamp": now.to_iso8601_string()
            }
            for winner in winners
        ]

        await self.bot.giveaways.update_one(
            {"_id": giveaway["_id"]},
            {"$set": {"winners_list": new_winners}}
        )

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        """
        Listener for giveaway participation buttons.
        """
        #i normally use ctx.data.custom_id, but i actually kinda like this lol
        if ctx.component.custom_id.startswith("giveaway_"):
            giveaway_id = ctx.component.custom_id.split("_")[1]

            # Defer the interaction to allow time for processing
            await ctx.response.defer(ephemeral=True)

            # Fetch giveaway from the database
            giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
            if not giveaway:
                await ctx.send("This giveaway no longer exists.", ephemeral=True)
                return

            # Check if the giveaway has ended
            if giveaway.get("end_time"):
                end_time = giveaway["end_time"]
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)

                if datetime.now(timezone.utc) > end_time:
                    await ctx.send("This giveaway has already ended!", ephemeral=True)
                    return


            # Check if the user has already entered
            if str(ctx.user.id) in giveaway.get("entries", []):
                await ctx.send("You have already entered this giveaway!", ephemeral=True)
                return

            # Check for roles allow/deny rules
            user_roles = [str(role.id) for role in ctx.user.roles]
            roles_mode = giveaway.get("roles_mode", "allow")
            allowed_roles = giveaway.get("roles", [])

            if roles_mode == "deny" and any(role in allowed_roles for role in user_roles) is False:
                await ctx.send("You are not allowed to enter this giveaway.", ephemeral=True)
                return
            elif roles_mode == "allow" and any(role in allowed_roles for role in user_roles):
                await ctx.send("You are not allowed to enter this giveaway.", ephemeral=True)
                return

            # Check profile picture requirement
            if giveaway.get("profile_picture_required") and ctx.user.avatar is None:
                await ctx.send("You need a profile picture to enter this giveaway.", ephemeral=True)
                return

            # Check Clash account requirement
            if giveaway.get("coc_account_required"):
                results = await self.bot.link_client.get_linked_players(ctx.user.id)
                if not results:
                    await ctx.send(
                        "You need a linked Clash account to enter this giveaway.",
                        ephemeral=True
                    )
                    return

            await self.bot.giveaways.update_one(
                {"_id": giveaway_id},
                {"$push": {"entries": str(ctx.user.id)}}
            )
            try:
                existing_job = self.bot.scheduler.get_job(giveaway_id)
                if existing_job:
                    self.bot.scheduler.remove_job(giveaway_id)

                self.bot.scheduler.add_job(
                    self.update_button,
                    trigger='date',
                    id=giveaway_id,
                    run_date=pend.now(tz=pend.UTC).add(minutes=1),
                    args=[giveaway_id, ctx.message]
                )

                await ctx.send("You successfully joined the giveaway! 🎉", ephemeral=True)
            except disnake.NotFound:
                await ctx.send("The giveaway message could not be found.", ephemeral=True)


def setup(bot):
    bot.add_cog(GiveawayEvents(bot))
