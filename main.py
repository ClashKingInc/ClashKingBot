import os
import disnake
from disnake import Client
from disnake.ext import commands
import traceback
from utils.clash import client
import asyncpraw

#db collections
usafam = client.usafam
server = usafam.server
clans = usafam.clans
whitelist = usafam.whitelist
banlist = usafam.banlist


TOKEN = os.getenv("TOKEN")
discClient = Client()
intents = disnake.Intents().default()
intents.members = True
bot = commands.Bot(command_prefix="??", help_command=None, intents=intents,
    sync_commands_debug=False, sync_permissions=True)

initial_extensions = (
    "BackgroundLoops.autoboard_loop",
    "BackgroundLoops.leaderboards",
    "Family & Clans.bans",
    "Family & Clans.clan",
    "Family & Clans.donations",
    "Family & Clans.family",
    "Family & Clans.familystats",
    "Link & Eval.link",
    "Link & Eval.eval",
    "Setups.addclans",
    "Setups.autoboard",
    "Setups.evalsetup",
    "Setups.voice_countdowns",
    "Setups.welcome_messages",
    #"Setups.clan_boards",
    "Setups.joinleave",
    "Setups.clan_capital",
    "Utility.army",
    "Utility.awards",
    "Utility.boost",
    "Utility.profile",
    "War & CWL.cwl",
    "War & CWL.war",
    "discord_events",
    "help",
    "other",
    "owner_commands",
    "settings",
    "testing",
    "ProfilePic.pfp"
)

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


async def reddit_task():
    await bot.wait_until_ready()
    print("feed")
    count = 0
    sub = await reddit.subreddit(subreddit)
    async for submission in sub.stream.submissions():
        if count < 100:  # This removes the 100 historical submissions that SubredditStream pulls.
            count += 1
            continue

        if submission.link_flair_text == 'Searching':
            # submission: asyncpraw.Reddit.submission
            text = submission.selftext
            title = submission.title

            for x in range(6, 9):
                test = "th" + str(x + 6)
                test2 = "th " + str(x + 6)
                test3 = "TH" + str(x + 6)
                test4 = "TH " + str(x + 6)
                test5 = "Townhall" + str(x + 6)
                test6 = "Townhall " + str(x + 6)
                test7 = "townhall" + str(x + 6)
                test8 = "townhall " + str(x + 6)
                test9 = "Town hall" + str(x + 6)
                test10 = "Town hall " + str(x + 6)
                test11 = "town hall" + str(x + 6)
                test12 = "town hall " + str(x + 6)
                test13 = "Th" + str(x + 6)
                test14 = "Th " + str(x + 6)


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
                    channel = bot.get_channel(981051561172156518)
                    # await channel.send("<@&818564701910597683>")
                    embed = disnake.Embed(title=f'{submission.title}', description=submission.selftext
                                                                                   + f'\n{submission.score} points | [Link]({submission.url}) | [Comments](https://www.reddit.com/r/{subreddit}/comments/{submission.id})')

                    await channel.send(content="<@&916493154243457074> <@326112461369376770>", embed=embed)

if __name__ == "__main__":
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    bot.loop.create_task(reddit_task())
    bot.run(TOKEN)
