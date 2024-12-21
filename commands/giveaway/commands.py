from random import sample, choices

import disnake
from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands
from datetime import datetime, timedelta
import uuid
import base64

from discord.autocomplete import Autocomplete
from utility.discord_utils import check_commands


class GiveawayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="giveaway", description="Manage all giveaway-related commands.")
    async def giveaway(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Parent command for managing giveaways.
        """
        pass

    # Sub-command: Giveaway Dashboard
    @giveaway.sub_command(name="dashboard", description="Generate a link to access the giveaway dashboard.")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def giveaway_dashboard(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Generate a tokenized URL for the giveaway dashboard.
        """
        # Generate a unique token
        token = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode("utf-8")

        # Save the token to the database
        token_data = {
            "server_id": ctx.guild.id,
            "token": token,
            "type": "giveaway",
            "expires_at": datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        }
        await self.bot.tokens_db.insert_one(token_data)

        # Generate the dashboard URL
        dashboard_url = f"https://api.clashking.xyz/giveaway/dashboard?token={token}"

        # Send the URL to the user
        embed = disnake.Embed(
            title="🎉 Giveaway Dashboard",
            description=f"Click the link below to manage giveaways for **{ctx.guild.name}**:",
            color=disnake.Color.green()
        )
        embed.add_field(name="Access Link", value=f"[Open Dashboard]({dashboard_url})", inline=False)
        embed.set_footer(text="This link will expire in 1 hour.")
        await ctx.send(embed=embed, ephemeral=True)

    # Sub-command: Reroll Winner
    @giveaway.sub_command(name="reroll", description="Reroll one or more winners of a giveaway using mentions.")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def giveaway_reroll(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            giveaway_name: str = commands.Param(
                description="The ID of the giveaway to reroll.",
                autocomplete=Autocomplete.recent_giveaway_ids
            ),
            users_to_replace: str = commands.Param(description="Mention the users to replace (@user1 @user2)."),
            reason: str = commands.Param(default=None, description="Reason for the reroll (optional).")
    ):
        """
        Reroll winners of a giveaway by replacing specified users.
        """
        giveaway_id = giveaway_name.split(" | ")[1]
        # Fetch the giveaway data
        giveaway = await self.bot.giveaways.find_one({"_id": giveaway_id})
        if not giveaway:
            await ctx.send(f"❌ Giveaway with ID `{giveaway_id}` not found.", ephemeral=True)
            return

        participants = giveaway.get("entries", [])
        if not participants:
            await ctx.send("❌ There are no participants for this giveaway.", ephemeral=True)
            return

        boosters = giveaway.get("boosters", [])

        # Parse the mentions into user IDs
        user_ids_to_replace = [mention.strip("<@!>") for mention in users_to_replace.split()]
        user_ids_to_replace = [uid for uid in user_ids_to_replace if uid.isdigit()]

        # Validate the mentioned users
        invalid_users = [uid for uid in user_ids_to_replace if uid not in participants]
        if invalid_users:
            invalid_mentions = ", ".join([f"<@{uid}>" for uid in invalid_users])
            await ctx.send(
                f"❌ The following users are not participants of this giveaway: {invalid_mentions}", ephemeral=True
            )
            return

        # Ensure we have enough eligible participants to replace
        eligible_participants = [p for p in participants if p not in user_ids_to_replace]
        if len(eligible_participants) < len(user_ids_to_replace):
            await ctx.send(
                f"❌ Not enough eligible participants to replace {len(user_ids_to_replace)} users.", ephemeral=True
            )
            return

        # Calculate weights based on boosters
        weights = []
        for participant in eligible_participants:
            weight = 1.0
            for booster in boosters:
                if participant in booster["roles"]:
                    weight *= booster["value"]
            weights.append(weight)

        # Select new winners
        new_winners = choices(eligible_participants, weights=weights, k=len(user_ids_to_replace))

        # Format the announcement
        old_winner_mentions = ", ".join([f"<@{uid}>" for uid in user_ids_to_replace])
        new_winner_mentions = ", ".join([f"<@{uid}>" for uid in new_winners])
        reason_text = f"**Reason for Reroll:** {reason}" if reason else ""

        # Create the embed
        embed = Embed(
            title=f"🎉 Reroll Winner(s) for {giveaway['prize']} 🎉",
            description=(
                f"**Replaced Winner(s):** {old_winner_mentions}\n"
                f"**New Winner(s):** {new_winner_mentions}\n"
                f"{reason_text}\n\n"
                f"**Total Participants:** {len(participants)}"
            ),
            color=disnake.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Rerolled by {ctx.author.name}")

        # Send the announcement in the giveaway's channel
        channel_id = giveaway["channel_id"]
        channel = await self.bot.getch_channel(int(channel_id))

        if not channel:
            await ctx.send("❌ Could not find the channel associated with the giveaway.", ephemeral=True)
            return

        await channel.send(content=f"{new_winner_mentions}", embed=embed)

        # Update the database with the rerolled winners
        await self.bot.giveaways.update_one(
            {"_id": giveaway_id},
            {"$push": {"rerolled_winners": {"replaced": user_ids_to_replace, "new": new_winners}}}
        )

        # Confirm the action to the administrator
        await ctx.send(
            f"✅ Reroll completed. New winners have been announced in <#{channel_id}>.", ephemeral=True
        )

def setup(bot):
    bot.add_cog(GiveawayCommands(bot))
