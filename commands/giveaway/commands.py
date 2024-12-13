import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
from bson import ObjectId
import uuid
import base64

class GiveawayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="giveaway", description="Manage all giveaway-related commands.")
    async def giveaway(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Parent command for managing giveaways.
        """
        pass

    # Sub-command: Create Giveaway
    @giveaway.sub_command(name="create", description="Create a new giveaway.")
    @commands.has_permissions(administrator=True)
    async def create_giveaway(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        prize: str = commands.Param(description="Prize for the giveaway"),
        start_time: str = commands.Param(description="Start time in UTC (YYYY-MM-DD HH:MM format)"),
        end_time: str = commands.Param(description="End time in UTC (YYYY-MM-DD HH:MM format)"),
        winners: int = commands.Param(description="Number of winners"),
        channel: disnake.TextChannel = commands.Param(description="Channel to post the giveaway"),
        mentions: str = commands.Param(description="Roles/mentions (comma-separated)", default=""),
        image_url: str = commands.Param(description="URL of the image for the giveaway", default=""),
        text_above_embed: str = commands.Param(description="Text above the embed", default="")
    ):
        """
        Create a giveaway directly from the bot.
        """
        try:
            # Validate date inputs
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M")

            if end_time <= start_time:
                await ctx.send("The end time must be after the start time!", ephemeral=True)
                return

            # Generate the embed
            embed = disnake.Embed(
                title="🎉 Giveaway 🎉",
                description=(
                    f"**Prize**: {prize}\n"
                    f"**Winners**: {winners}\n"
                    f"**Ends at**: <t:{int(end_time.timestamp())}:F>\n"
                ),
                color=disnake.Color.blurple()
            )
            if image_url:
                embed.set_image(url=image_url)
            embed.set_footer(text=f"Organized by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

            # Add text above the embed if provided
            content = text_above_embed
            if mentions:
                content += "\n" + ", ".join([mention.strip() for mention in mentions.split(",")])

            # Create a button for participation
            button = disnake.ui.Button(
                label="🎟️ Enter Giveaway",
                style=disnake.ButtonStyle.green,
                custom_id=f"giveaway_{uuid.uuid4()}"
            )

            # Send the giveaway message
            message = await channel.send(content=content, embed=embed, components=[disnake.ui.ActionRow(button)])

            # Save the giveaway to the database
            giveaway_data = {
                "server_id": ctx.guild.id,
                "prize": prize,
                "start_time": start_time,
                "end_time": end_time,
                "winners": winners,
                "channel_id": channel.id,
                "message_id": message.id,
                "status": "scheduled",
                "mentions": mentions.split(","),
                "text_above_embed": text_above_embed,
                "image_url": image_url,
                "entries": [],
                "created_by": ctx.author.id
            }
            await self.bot.giveaways.insert_one(giveaway_data)

            # Confirm creation
            await ctx.send(f"Giveaway created successfully in {channel.mention}!", ephemeral=True)

        except ValueError:
            await ctx.send("Invalid date format! Use YYYY-MM-DD HH:MM (UTC).", ephemeral=True)

    # Sub-command: Giveaway Dashboard
    @giveaway.sub_command(name="dashboard", description="Generate a link to access the giveaway dashboard.")
    @commands.has_permissions(administrator=True)
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
        dashboard_url = f"https://localhost:8000/giveaway/dashboard?token={token}"

        # Send the URL to the user
        embed = disnake.Embed(
            title="🎉 Giveaway Dashboard",
            description=f"Click the link below to manage giveaways for **{ctx.guild.name}**:",
            color=disnake.Color.green()
        )
        embed.add_field(name="Access Link", value=f"[Open Dashboard]({dashboard_url})", inline=False)
        embed.set_footer(text="This link will expire in 1 hour.")
        await ctx.send(embed=embed, ephemeral=True)

    # Sub-command: Manage Giveaway
    @giveaway.sub_command(name="manage", description="Manage an existing giveaway.")
    @commands.has_permissions(administrator=True)
    async def manage_giveaway(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        giveaway_id: str = commands.Param(description="ID of the giveaway to manage"),
        action: str = commands.Param(choices=["Edit", "Delete"], description="Action to perform")
    ):
        """
        Manage giveaways directly from the bot.
        """
        # Fetch the giveaway from the database
        giveaway = await self.bot.giveaways.find_one({"_id": ObjectId(giveaway_id)})

        if not giveaway:
            await ctx.send("Giveaway not found!", ephemeral=True)
            return

        if action == "Delete":
            await self.bot.giveaways.delete_one({"_id": ObjectId(giveaway_id)})
            await ctx.send("Giveaway deleted successfully.", ephemeral=True)

        elif action == "Edit":
            # Redirect the user to the dashboard for editing
            token = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode("utf-8")
            dashboard_url = f"https://api.clashking.xyz/giveaway/dashboard?token={token}"
            await ctx.send(f"Edit the giveaway here: {dashboard_url}", ephemeral=True)


def setup(bot):
    bot.add_cog(GiveawayCommands(bot))
