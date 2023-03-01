from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
import asyncpraw
import os
import disnake

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
        self.sent = []


    async def reddit_task(self):
        print("feed")
        while True:
            try:
                count = 0
                sub = await reddit.subreddit(subreddit)
                async for submission in sub.stream.submissions():
                    if count < 100:  # This removes the 100 historical submissions that SubredditStream pulls.
                        count += 1
                        continue

                    if submission.id in self.sent:
                        continue
                    if len(self.sent) == 100:
                        del self.sent[:50]
                    self.sent.append(submission.id)

                    if submission.link_flair_text == 'Searching':
                        text = submission.selftext
                        title = submission.title

                        match = True

                        if match:
                            results = self.bot.server_db.find({"reddit_feed": {"$ne": None}})
                            limit = await self.bot.server_db.count_documents(filter={"reddit_feed": {"$ne": None}})
                            for r in await results.to_list(length=limit):
                                try:
                                    channel = r.get("reddit_feed")
                                    channel = await self.bot.fetch_channel(channel)
                                    role = r.get("reddit_role")
                                    embed = disnake.Embed(title=f'{submission.title}',
                                                          description=submission.selftext
                                                                      + f'\n{submission.score} points | [Link]({submission.url}) | [Comments](https://www.reddit.com/r/{subreddit}/comments/{submission.id})',
                                                          color=disnake.Color.green())
                                    buttons = disnake.ui.ActionRow()
                                    buttons.append_item(disnake.ui.Button(label="Post Link", emoji=self.bot.emoji.reddit_icon.partial_emoji, url=submission.url))

                                    if role is not None:
                                        await channel.send(content=f"<@&{role}>",
                                                       embed=embed, components=buttons)
                                    else:
                                        await channel.send(embed=embed, components=buttons)

                                except (disnake.NotFound, disnake.Forbidden):
                                    serv = r.get("server")
                                    await self.bot.server_db.update_one({"server": serv}, {"$set": {"reddit_feed": None, "reddit_role" : None}})
            except Exception as e:
                print(e)
                continue

def setup(bot: CustomClient):
    bot.add_cog(reddit_feed(bot))