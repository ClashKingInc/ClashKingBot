import uuid

import disnake
from disnake.ext import commands

from classes.bot import CustomClient


class Suggestions(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(
        name='suggest',
        description='Suggest a feature for the bot',
        guild_ids=[923764211845312533],
    )
    async def suggest(self, ctx: disnake.ApplicationCommandInteraction, topic: str, description: str):
        suggestion_id = str(uuid.uuid4())
        suggestion = {
            '_id': suggestion_id,
            'topic': topic,
            'description': description,
            'votes': 0,
            'voters': [],  # Track voters to ensure one vote per person
        }
        result = await self.bot.suggestions.insert_one(suggestion)

        # Send to suggestion channel
        channel = await self.bot.getch_channel(1206000739143647372)
        embed = disnake.Embed(title=topic, description=description, color=0x000000)  # Starting as black
        embed.set_footer(text=f'Suggestion ID: {str(suggestion_id)}')
        message = await channel.send(
            embed=embed,
            components=[
                disnake.ui.Button(
                    style=disnake.ButtonStyle.green,
                    label='Upvote',
                    custom_id=f'upvote_{suggestion_id}',
                ),
            ],
        )

        # Create a thread for discussion
        await message.create_thread(name=f'Suggestion: {topic}')
        await ctx.response.send_message('Your suggestion has been posted!', ephemeral=True)

        # Update the leaderboard
        await self.update_leaderboard(channel)

    async def update_leaderboard(self, channel: disnake.TextChannel, edit=False):
        top_suggestions: list = await self.bot.suggestions.find().sort('votes', -1).limit(10).to_list(length=None)

        # Start building the embed
        embed = disnake.Embed(
            title='Top Suggestions Leaderboard',
            description='Here are the top 10 suggestions based on community votes:',
            color=disnake.Color.green(),  # Green color for the leaderboard
        )

        for index, suggestion in enumerate(top_suggestions):
            embed.add_field(
                name=f"{index + 1}. {suggestion['topic']}",
                value=f"Votes: {suggestion['votes']} | Description: {suggestion['description'][:100]}",
                inline=False,
            )
        embed.set_footer(text='Use /suggest to add your suggestions here!')
        if not edit:

            def is_leaderboard_embed(m):
                # Check if the message is by the bot and has at least one embed
                if m.author == self.bot.user and m.embeds:
                    for embed in m.embeds:
                        # Check if the embed's title matches the leaderboard title
                        if embed.title == 'Top Suggestions Leaderboard':
                            return True
                return False

            # Remove the old leaderboard messages
            await channel.purge(limit=100, check=is_leaderboard_embed)
            # Send the new leaderboard embed
            await channel.send(embed=embed)
        else:
            messages = await channel.history(limit=1).flatten()
            last_message = messages[0]
            await last_message.edit(embed=embed)

    @commands.slash_command(description='Remove a completed suggestion', guild_ids=[923764211845312533])
    @commands.is_owner()
    async def remove_suggestion(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        suggestion_id: str = commands.Param(description='The ID of the suggestion to remove'),
    ):
        await self.bot.suggestions.delete_one({'_id': suggestion_id})
        await ctx.response.send_message('Suggestion removed.', ephemeral=True)
        # Optionally, update the leaderboard here if you want it to refresh upon removal
        channel = await self.bot.getch_channel(1206000739143647372)
        await self.update_leaderboard(channel)

    @commands.slash_command(guild_ids=[923764211845312533])
    @commands.is_owner()
    async def ping_upvoters(
        self,
        inter: disnake.ApplicationCommandInteraction,
        suggestion_id: str = commands.Param(description='The ID of the suggestion'),
    ):
        # Fetch the suggestion from the database
        suggestion = await self.bot.suggestions.find_one({'_id': suggestion_id})
        if not suggestion:
            await inter.response.send_message('Suggestion not found.', ephemeral=True)
            return

        upvoters = suggestion.get('voters', [])
        if not upvoters:
            await inter.response.send_message('No upvotes for this suggestion.', ephemeral=True)
            return

        # Construct the message to ping all upvoters
        # Discord has a limit on message length and the number of users you can mention in a single message,
        # so you may need to split this into multiple messages if there are many upvoters.
        ping_message = ' '.join([f'<@{user_id}>' for user_id in upvoters])
        # Send the message in the current channel or a specific channel
        await inter.channel.send(ping_message[:2000])  # Trim to 2000 characters to meet Discord's limit
        await inter.response.send_message('Upvoters pinged.', ephemeral=True)

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        custom_id: str = ctx.component.custom_id
        if custom_id.startswith('upvote_'):
            vote, suggestion_id = custom_id.split('_')

            user_id = str(ctx.author.id)
            suggestion = await self.bot.suggestions.find_one({'_id': suggestion_id})
            if user_id in suggestion['voters']:
                await ctx.response.send_message('You have already voted on this suggestion.', ephemeral=True)
                return
            await self.bot.suggestions.update_one(
                {'_id': suggestion_id},
                {'$inc': {'votes': 1}, '$push': {'voters': user_id}},
            )
            votes = suggestion['votes'] + 1

            # Calculate the new color
            # Clamp votes between 0 and 10 for color calculation
            clamped_votes = max(0, min(votes, 10))
            green_intensity = int((clamped_votes / 10) * 255)
            new_color = 0x000000 + (green_intensity << 8)  # Shift green component to the right place

            # Update the embed with the new color and votes
            new_embed = disnake.Embed(
                title=suggestion['topic'],
                description=suggestion['description'],
                color=new_color,  # Starting as black
            )
            new_embed.add_field(name='Votes', value=str(votes))
            new_embed.set_footer(text=f'Suggestion ID: {str(suggestion_id)}')
            await ctx.message.edit(embed=new_embed)
            channel = await self.bot.getch_channel(1206000739143647372)
            await self.update_leaderboard(channel, edit=True)
            await ctx.response.defer()


def setup(bot: CustomClient):
    bot.add_cog(Suggestions(bot))
