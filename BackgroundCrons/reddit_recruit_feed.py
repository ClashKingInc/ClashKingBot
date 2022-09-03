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

                        for x in range(4, 9):
                            test = f"th{str(x + 6)}"
                            test2 = f"th {str(x + 6)}"
                            test3 = f"TH{str(x + 6)}"
                            test4 = f"TH {str(x + 6)}"
                            test5 = f"Townhall{str(x + 6)}"
                            test6 = f"Townhall {str(x + 6)}"
                            test7 = f"townhall{str(x + 6)}"
                            test8 = f"townhall {str(x + 6)}"
                            test9 = f"Town hall{str(x + 6)}"
                            test10 = f"Town hall {str(x + 6)}"
                            test11 = f"town hall{str(x + 6)}"
                            test12 = f"town hall {str(x + 6)}"
                            test13 = f"Th{str(x + 6)}"
                            test14 = f"Th {str(x + 6)}"

                            a = test in text or test in title
                            b = test2 in text or test2 in title
                            c = test3 in text or test3 in title
                            d = test4 in text or test4 in title
                            e = test5 in text or test5 in title
                            f = test6 in text or test6 in title
                            g = test7 in text or test7 in title
                            h = test8 in text or test8 in title
                            i = test9 in text or test9 in title
                            j = test10 in text or test10 in title
                            k = test11 in text or test11 in title
                            l = test12 in text or test12 in title
                            m = test13 in text or test13 in title
                            n = test14 in text or test14 in title

                            match = a or b or c or d or e or f or g or h or i or j or k or l or m or n

                            if match:
                                results = self.bot.server_db.find({"reddit_feed": {"$ne": None}})
                                limit = await self.bot.server_db.count_documents(filter={"reddit_feed": {"$ne": None}})
                                for r in await results.to_list(length=limit):
                                    try:
                                        channel = r.get("reddit_feed")
                                        serv = r.get("server")
                                        channel = self.bot.get_channel(channel)
                                        guild = self.bot.get_guild(serv)
                                        role = r.get("reddit_role")
                                        ranking = []
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