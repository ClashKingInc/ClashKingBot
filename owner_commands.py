import asyncio

import disnake
from disnake.ext import commands
from jokeapi import Jokes
import asyncpraw
from utils.clash import coc_client

clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0

class OwnerCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reload', hidden=True)
    async def _reload(self,ctx, *, module: str):
        """Reloads a module."""
        if ctx.message.author.id == 706149153431879760:
            try:
                self.bot.unload_extension(module)
                self.bot.load_extension(module)
            except:
                await ctx.send('<a:no:862552093324083221> Could not reload module.')
            else:
                await ctx.send('<a:check:861157797134729256> Reloaded module successfully')
        else:
            await ctx.send("You aren't magic. <:PS_Noob:783126177970782228>")

    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")

    @commands.command(name='servers')
    @commands.is_owner()
    async def serversmm(self, ctx):
        text = ""
        guilds = self.bot.guilds
        for guild in guilds:
            name = guild.name
            text += f"{name} | {len(guild.members)}\n"

        embed = disnake.Embed(title=f"{len(guilds)} servers", description=text,
                              color=disnake.Color.green())

        await ctx.send(embed=embed)

    @commands.command(name="joke")
    async def joke(self, ctx, category=None):
        category = []
        cat_list = ["Dark", "Pun"]
        if category is not None and category in cat_list:
            category.append(category)
        j = await Jokes()  # Initialise the class
        if category is not None:
            joke = await j.get_joke(category=category)
        else:
            joke = await j.get_joke() # Retrieve a random joke
        if joke["type"] == "single":  # Print the joke
            await ctx.send(joke["joke"])
        else:
            msg = await ctx.send(joke["setup"] + f"\n\n**10**")
            for x in range(9, 0, -1):
                await msg.edit(content=joke["setup"] + f"\n\n**{x}**")
                await asyncio.sleep(1)
            await msg.edit(content=joke["setup"] + "\n\n" + joke["delivery"])

    @commands.command(name="feed")
    @commands.is_owner()
    async def feed(self, ctx):
        print("feed")


        count = 0
        sub = await reddit.subreddit(subreddit)
        async for submission in sub.stream.submissions():
            if count < 100:  # This removes the 100 historical submissions that SubredditStream pulls.
                count += 1
                continue

            if submission.link_flair_text == 'Searching':
                #submission: asyncpraw.Reddit.submission
                text = submission.selftext
                title = submission.title

                for x in range(6, 9):
                    test = "th" + str(x + 6)
                    test2 = "th " + str(x + 6)
                    test3 = "TH" + str(x + 6)
                    test4 = "TH " + str(x + 6)
                    test5 = "Townhall " + str(x + 6)
                    test6 = "Town hall" + str(x + 6)
                    test7 = "Town hall " + str(x + 6)
                    test8 = "Th" + str(x + 6)
                    test9 = "Th " + str(x + 6)

                    a = test in text or test in title
                    b = test2 in text or test2 in title
                    c = test3 in text or test3 in title
                    d = test4 in text or test4 in title
                    e = test5 in text or test5 in title
                    f = test6 in text or test6 in title
                    g = test7 in text or test7 in title
                    h = test8 in text or test8 in title
                    i = test9 in text or test9 in title

                    match = a or b or c or d or e or f or g or h or i

                    if match:
                        channel = self.bot.get_channel(981051561172156518)
                        # await channel.send("<@&818564701910597683>")
                        embed = disnake.Embed(title=f'{submission.title}', description=submission.selftext
                                               + f'\n{submission.score} points | [Link]({submission.url}) | [Comments](https://www.reddit.com/r/{subreddit}/comments/{submission.id})')

                        await channel.send(content="<@&916493154243457074> <@326112461369376770>",embed=embed)


    @commands.command("hunt")
    @commands.is_owner()
    async def hunt(self, ctx):
        global known_streak
        global count
        channel = ctx.message.channel
        global clan_tags
        global list_size
        scanned = []
        while True:
            # print(clan_tags)
            list_size = len(clan_tags)
            clan_tags = list(dict.fromkeys(clan_tags))
            hold = clan_tags
            async for clan in coc_client.get_clans(clan_tags):
                scanned.append(clan.tag)
                count += 1
                if clan.war_win_streak >= 35:
                    if clan.member_count >= 10:
                        if str(clan.chat_language) == "English" or str(clan.chat_language) == "None":
                            description = clan.description
                            rest = ""
                            if "discord.gg" in description:
                                rest = description.partition("discord.gg")[2]
                                rest = "discord.gg" + rest
                            location = ""
                            try:
                                location = str(clan.location)
                            except:
                                pass

                            if clan.tag not in known_streak:
                                await channel.send(
                                    f"{clan.name} | {clan.tag} | ({clan.member_count}/50) - {clan.war_win_streak} wins | {location} | {rest}")
                            known_streak.append(clan.tag)

                clan_tags.remove(clan.tag)

            print(len(hold))
            for tag in hold:
                try:
                    warlog = await coc_client.get_warlog(clan_tag=tag)
                except:
                    continue
                for war in warlog:
                    try:
                        if war.opponent.tag not in clan_tags and war.opponent.tag not in scanned:
                            clan_tags.append(war.opponent.tag)
                    except:
                        continue



    @commands.command("count")
    async def coun(self, ctx):
        global count
        global list_size
        global clan_tags
        await ctx.send(f"{count} clans searched through\n"
                       f"Previous Search Size: {list_size} clans\n"
                       f"Current List Size: {len(clan_tags)} clans")

    async def get_warlog(self,clan, channel):
        global clan_tags
        try:
            warlog = await coc_client.get_warlog(clan_tag=clan.tag)
        except:
            return
        for war in warlog:
            try:
                clan = await coc_client.get_clan(tag=war.opponent.tag)
                if war.opponent.tag not in clan_tags:
                    if clan.war_win_streak >= 35:
                        if clan.member_count >= 10:
                            if str(clan.chat_language) == "English" or str(clan.chat_language) == "None":
                                description = clan.description
                                rest = ""
                                if "discord.gg" in description:
                                    rest = description.partition("discord.gg")[2]
                                location = ""
                                try:
                                    location = str(clan.location)
                                except:
                                    pass

                                await channel.send(f"{clan.name} | {clan.tag} | ({clan.member_count}/50) - {clan.war_win_streak} wins | {location} | {rest}")
                    clan_tags.append(war.opponent.tag)
            except:
                continue

def setup(bot: commands.Bot):
    bot.add_cog(OwnerCommands(bot))