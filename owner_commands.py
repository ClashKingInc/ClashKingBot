import asyncio

import disnake
from disnake.ext import commands
from jokeapi import Jokes
import asyncpraw
from utils.clash import coc_client, client, getClan

usafam = client.usafam
banlist = usafam.banlist
server = usafam.server
clans = usafam.clans
clancapital = usafam.clancapital

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

    @commands.command(name="fixcapital", hidden=True)
    async def fixcapital(self, ctx):
        tags = []
        tracked = clancapital.find()
        limit = await clancapital.count_documents(filter={})
        for document in await tracked.to_list(length=limit):
            tag = document.get("tag")
            if tag not in tags:
                tags.append(tag)

        async for player in coc_client.get_players(tags):
            if player.clan is None:
                continue
            await clancapital.update_one({"tag": player.tag}, {'$set': {
                "clan": player.clan.tag,
            }})

        await ctx.send("done")


    @commands.command(name="testraid")
    async def testraid(self, ctx, tag):

        text = ""
        clan = await getClan(tag)

        tracked = clans.find({"tag": f"{clan.tag}"})
        limit = await clans.count_documents(filter={"tag": f"{clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue

            try:
                clancapital_channel = await server.fetch_channel(clancapital_channel)
                if clancapital_channel is None:
                    continue
            except:
                continue

            embed = disnake.Embed(
                description=f"Test Player donated <:capitalgold:987861320286216223>1000"
                , color=disnake.Color.green())

            embed.set_footer(icon_url=clan.badge.url, text=clan.name)

            try:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send =ow.send_messages
                await clancapital_channel.send(embed=embed)
                text += f"{server.name} : Successful\n> Send Messages Perm: {send}\n"
            except Exception as e:
                member = await server.getch_member(self.bot.user.id)
                ow = clancapital_channel.overwrites_for(member)
                send = ow.send_messages
                text += f"{server.name} : Not Successful\n> Send Messages Perm: {send}\n> {str(e)[0:1000]}\n"

        embed = disnake.Embed(title=f"Test Raid {clan.name}", description=text, color=disnake.Color.green())
        await ctx.send(embed=embed)

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