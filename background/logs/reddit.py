import asyncpraw
import os
import disnake
import re
import coc

from disnake.ext import commands
from classes.bot import CustomClient
from utility.player_pagination import button_pagination
from datetime import datetime


subreddit = "ClashOfClansRecruit"
secret = os.getenv("SECRET")
RPW = os.getenv("RPW")
reddit = asyncpraw.Reddit(
    client_id="-dOCgLIHqUJK7g",
    client_secret= secret,
    username="Powerful-Flight2605",
    password=RPW,
    user_agent="Reply Recruit"
)

class reddit_feed(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.loop.create_task(self.reddit_task())

    async def reddit_task(self):
        while True:
            try:
                count = 0
                sub = await reddit.subreddit(subreddit)
                async for submission in sub.stream.submissions():
                    if count < 100:  # This removes the 100 historical submissions that SubredditStream pulls.
                        count += 1
                        continue
                    if submission.link_flair_text == 'Searching':
                        text = f"{submission.selftext} {submission.title}"
                        tags = re.findall('[#PYLQGRJCUVOpylqgrjcuvo0289]{5,11}', text)
                        player = None
                        for tag in tags:
                            player = await self.bot.getPlayer(player_tag=tag)
                            if player is not None:
                                break

                        results = await self.bot.server_db.find({"reddit_feed": {"$ne": None}}).to_list(length=None)
                        for r in results:
                            try:
                                channel = await self.bot.getch_channel(r.get("reddit_feed"), raise_exception=True)
                                role = r.get("reddit_role")
                                embed = disnake.Embed(title=f'{submission.title}',
                                                      description=submission.selftext
                                                                  + f'\n{submission.score} points | [Link]({submission.url}) | [Comments](https://www.reddit.com/r/{subreddit}/comments/{submission.id})',
                                                      color=disnake.Color.green())
                                buttons = disnake.ui.ActionRow()
                                buttons.append_item(disnake.ui.Button(label="Post Link", emoji=self.bot.emoji.reddit_icon.partial_emoji, url=submission.url))
                                if tags and player is not None:
                                    buttons.append_item(disnake.ui.Button(label="Player Profile", emoji=self.bot.emoji.troop.partial_emoji, style=disnake.ButtonStyle.green, custom_id=f"redditplayer_{player.tag}"))

                                if role is not None:
                                    await channel.send(content=f"<@&{role}>",
                                                   embed=embed, components=buttons)
                                else:
                                    await channel.send(embed=embed, components=buttons)

                            except (disnake.NotFound, disnake.Forbidden):
                                serv = r.get("server")
                                #await self.bot.server_db.update_one({"server": serv}, {"$set": {"reddit_feed": None, "reddit_role" : None}})

            except Exception as e:
                print(e)
                continue

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "redditplayer_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True, with_message=True)
            tag = (str(ctx.data.custom_id).split("_"))[-1]
            msg = await ctx.original_message()
            player = await self.bot.getPlayer(player_tag=tag, custom=True)
            if player is None:
                return await ctx.edit_original_response(content="No player found.")
            await button_pagination(self.bot, ctx, msg, [player])


def setup(bot: CustomClient):
    bot.add_cog(reddit_feed(bot))