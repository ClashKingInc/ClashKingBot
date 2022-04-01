
from disnake.ext import commands, tasks
from utils.clashClient import client, pingToChannel, getClan, coc_client
import coc
from disnake_slash.utils.manage_components import wait_for_component, create_select, create_select_option, create_actionrow
import disnake
import datetime as dt
from main import check_commands

import math

usafam = client.usafam
clans = usafam.clans
server = usafam.server

start_time = 1643263200


class autoB(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.board_check.start()

    def cog_unload(self):
        self.board_check.cancel()

    @commands.group(name="autoboard", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def setupboard(self, ctx):
        embed = disnake.Embed(title="**For what command would you like an autoboard?**",
                               color=disnake.Color.green())

        select1 = create_select(
            options=[
                create_select_option("Top", value=f"Top"),
                create_select_option("Leaderboard", value=f"Leaderboard")
            ],
            placeholder="Choose your option",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)
        msg = await ctx.send(embed=embed, components=[action_row])

        chose = False
        while chose == False:
            try:
                res = await wait_for_component(self.bot, components=action_row, messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            chose = str(res.values[0])
            # print(chose)

        country = None
        if chose == "Leaderboard":
            rr = []
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})

            for clan in await tracked.to_list(length=limit):
                tag = clan.get("tag")
                c = await getClan(tag)
                location = str(c.location)
                if location not in rr:
                    rr.append(str(location))

            options = []
            for country in rr:
                options.append(create_select_option(label=f"{country}", value=f"{country}"))

            select1 = create_select(
                options=options,
                placeholder="Choose location",
                min_values=1,  # the minimum number of options a user must select
                max_values=1  # the maximum number of options a user can select
            )
            action_row = create_actionrow(select1)

            embed = disnake.Embed(title="**For what country would you like the leaderboard autoboard?**",
                                  color=disnake.Color.green())

            await msg.edit(embed=embed, components=[action_row])

            country = False
            while country == False:
                try:
                    res = await wait_for_component(self.bot, components=action_row, messages=msg, timeout=600)
                except:
                    return await msg.edit(components=[])

                if res.author_id != ctx.author.id:
                    await res.send(content="You must run the command to interact with components.", hidden=True)
                    continue

                country = str(res.values[0])

        times = ""
        valid_options = []
        real_times = []

        for x in range(0,24):
            valid_options.append(str(x+1))
            t = start_time + (x * 3600)
            real_times.append(t)
            rank = str(x+1)
            rank = rank.ljust(2)
            times+=(f"{rank}. <t:{t}:t>\n")

        embed = disnake.Embed(title="**Choose time for autoboard**",
                              description=f"What time should the autoboard post to a channel?\n"
                                          f"(Shows in local time)\n"
                                          f"{times}", color=disnake.Color.green())
        await msg.edit(embed=embed, components=[])

        time = None

        while time == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == ctx.message.author

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            # print(response)

            if response == "cancel":
                embed = disnake.Embed(description="**Command Canceled Chief**", color=disnake.Color.red())
                return await msg.edit(embed=embed)

            if response in valid_options:
                time = real_times[int(response) - 1]
            else:
                embed = disnake.Embed(title=f"`{response}` Not a valid option",
                                      description=f"What time should the autoboard post to a channel?\n"
                                                  f"(Shows in local time)\n"
                                                  f"{times}", color=disnake.Color.red())
                await msg.edit(embed=embed)

        utc_time = dt.datetime.utcfromtimestamp(time)
        hour = utc_time.hour

        embed = discord.Embed(title="**Channel**",
                              description=f"What is the channel to autopost in?\n Please make sure I have perms to send messages there.", color=discord.Color.green())
        await msg.edit(embed=embed)

        boardChannel = None

        while boardChannel == None:
            def check(message):
                ctx.message.content = message.content
                return message.content != "" and message.author == ctx.message.author

            r = await self.bot.wait_for("message", check=check, timeout=300)
            response = r.content
            await r.delete()
            boardChannel = await pingToChannel(ctx, response)

            if response == "cancel":
                embed = discord.Embed(description="**Command Canceled Chief**", color=discord.Color.red())
                return await msg.edit(embed=embed)

            if boardChannel is None:
                embed = discord.Embed(title="Sorry that channel is invalid. Please try again.",
                                      description=f"What is autoboard channel?",
                                      color=discord.Color.red())
                await msg.edit(embed=embed)
                continue

            c = boardChannel
            g = ctx.guild
            r = await g.fetch_member(824653933347209227)
            perms = c.permissions_for(r)
            send_msg = perms.send_messages
            if send_msg == False:
                embed = discord.Embed(
                    description=f"Missing Permissions.\nMust have `Send Messages` in the autoboard channel.\nTry Again. What is the channel?",
                    color=discord.Color.red())
                await msg.edit(embed=embed)
                boardChannel = None
                continue

        tex = ""
        if chose == "Top":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"topboardchannel": boardChannel.id}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"tophour": hour}})
        else:
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbboardChannel": boardChannel.id}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"country": country}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbhour": hour}})
            tex = f"\nCountry: {country}"

        time = f"<t:{time}:t>"
        embed = discord.Embed(title="**Autoboard Successfully Setup**",
                              description=f"Channel: {boardChannel.mention}\n"
                                          f"Time: {time}\n"
                                          f"Type: {chose}{tex}",
                              color=discord.Color.green())
        await msg.edit(embed=embed)



    @setupboard.group(name="remove", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def removeboard(self, ctx):
        embed = discord.Embed(title="**For what command would you like to remove autoboard?**",
                              color=discord.Color.green())

        select1 = create_select(
            options=[
                create_select_option("Top", value=f"Top"),
                create_select_option("Leaderboard", value=f"Leaderboard")
            ],
            placeholder="Choose your option",
            min_values=1,  # the minimum number of options a user must select
            max_values=1  # the maximum number of options a user can select
        )
        action_row = create_actionrow(select1)
        msg = await ctx.send(embed=embed, components=[action_row])

        chose = False
        while chose == False:
            try:
                res = await wait_for_component(self.bot, components=action_row, messages=msg, timeout=600)
            except:
                return await msg.edit(components=[])

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            chose = str(res.values[0])

        if chose == "Top":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"topboardchannel": None}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"tophour": None}})
        else:
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbboardChannel": None}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"country": None}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbhour": None}})

        embed = discord.Embed(description=f"{chose} autoboard has been removed.",
                              color=discord.Color.green())
        await msg.edit(embed=embed, components=[])



    @setupboard.group(name="list", pass_context=True, invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def boardlist(self, ctx):

        tbc = None
        th = None
        lbc = None
        lbh = None
        country = None

        results = await server.find_one({"server": ctx.guild.id})

        real_times = []

        for x in range(0, 24):
            t = start_time + (x * 3600)
            real_times.append(t)

        try:
            tbc =  results.get("topboardchannel")
            tbc = await pingToChannel(ctx, tbc)
            tbc = tbc.mention
        except:
            pass


        try:
            th = results.get("tophour")
            th = real_times[th - 6]
            th = f"<t:{th}:t>"
        except:
            pass

        try:
            lbc = results.get("lbboardChannel")
            lbc = await pingToChannel(ctx, lbc)
            lbc = lbc.mention
        except:
            pass

        try:
            lbh = results.get("lbhour")
            lbh = real_times[lbh - 6]
            lbh = f"<t:{lbh}:t>"
        except:
            pass

        try:
            country = results.get("country")
        except:
            pass

        embed = discord.Embed(title="**Autoboard List**",
                              description=f"`{ctx.prefix}top Board Channel`: {tbc}\n"
                                    f"`{ctx.prefix}top Post Time`: {th}\n"
                                    f"`{ctx.prefix}leaderboard Channel`: {lbc}\n"
                                    f"`{ctx.prefix}leaderboard Post Time`: {lbh}\n"
                                    f"`{ctx.prefix}leaderboard Country`: {country}\n",
                              color=discord.Color.green())
        await ctx.send(embed=embed)


    @tasks.loop(seconds=60)
    async def board_check(self):
        now = dt.datetime.utcnow()
        hour = now.hour
        minute = now.minute
        if minute == 55:
            print("here")
            results = server.find({"tophour": hour+1})
            limit = await server.count_documents(filter={"tophour": hour+1})
            for r in await results.to_list(length=limit):
                try:
                    channel = r.get("topboardchannel")
                    channel =  self.bot.get_channel(channel)
                    serv = r.get("server")
                    g = self.bot.get_guild(serv)
                    #print(g.name)

                    limit = 50

                    rankings = []
                    tracked = clans.find({"server": serv})
                    l = await clans.count_documents(filter={"server": serv})
                    if l == 0:
                        continue
                    for clan in await tracked.to_list(length=l):
                        tag = clan.get("tag")
                        clan = await getClan(tag)
                        for player in clan.members:
                            try:
                                playerStats = []
                                playerStats.append(player.name)
                                playerStats.append(player.trophies)
                                playerStats.append(player.clan.name)
                                playerStats.append(player.tag)
                                rankings.append(playerStats)
                            except:
                                continue

                    if limit > len(rankings):
                        limit = len(rankings)
                    ranking = sorted(rankings, key=lambda l: l[1], reverse=True)

                    embeds = []
                    length = math.ceil(limit / 50)
                    current_page = 0

                    for e in range(0, length):
                        rText = ''
                        max = limit
                        if (e + 1) * 50 < limit:
                            max = (e + 1) * 50
                        for x in range(e * 50, max):
                            # print(ranking[x])
                            place = str(x + 1) + "."
                            place = place.ljust(3)
                            rText += f"\u200e`{place}` \u200e<:trophy:956417881778815016> \u200e{ranking[x][1]} - \u200e{ranking[x][0]} | \u200e{ranking[x][2]}\n"

                        embed = discord.Embed(title=f"**Top {limit} {g.name} players**",
                                              description=rText)
                        embed.set_thumbnail(url=g.icon_url_as())
                        embeds.append(embed)
                    try:
                        await channel.send(embed=embeds[0])
                    except:
                        continue
                except:
                    pass

            results = server.find({"lbhour": hour+1})
            limit = await server.count_documents(filter={"lbhour": hour+1})
            for r in await results.to_list(length=limit):
                try:
                    channel = r.get("lbboardChannel")
                    channel =  self.bot.get_channel(channel)
                    serv = r.get("server")
                    g = self.bot.get_guild(serv)
                    country = r.get("country")

                    tags = []
                    tracked = clans.find({"server": g.id})
                    limit = await clans.count_documents(filter={"server": g.id})

                    for clan in await tracked.to_list(length=limit):
                        tag = clan.get("tag")
                        tags.append(tag)

                    text = ""
                    locations = await coc_client.search_locations(limit=None)
                    is_country = (country != "International")
                    country = coc.utils.get(locations, name=country, is_country=is_country)
                    country_names = country.name
                    # print(country.id)
                    rankings = await coc_client.get_location_clans(location_id=country.id)
                    # print(rankings)

                    x = 1
                    for clan in rankings:
                        rank = str(x)
                        rank = rank.ljust(2)
                        star = ""
                        if clan.tag in tags:
                            star = "⭐"
                        text += f"`\u200e{rank}`🏆`\u200e{clan.points}` \u200e{clan.name}{star}\n"
                        x += 1
                        if x == 26:
                            break

                    embed = discord.Embed(title=f"{country_names} Top 25 Leaderboard",
                                          description=text,
                                          color=discord.Color.green())
                    embed.set_thumbnail(url=g.icon_url_as())
                    try:
                        await channel.send(embed=embed)
                    except:
                        continue
                except:
                    pass

    @board_check.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(autoB(bot))