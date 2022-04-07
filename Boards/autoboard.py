
from disnake.ext import commands, tasks
from utils.clash import client, pingToChannel, getClan, coc_client
import coc
import disnake
import datetime as dt

import math

usafam = client.usafam
clans = usafam.clans
server = usafam.server




class autoB(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.board_check.start()

    def cog_unload(self):
        self.board_check.cancel()

    @commands.slash_command(name="autoboard")
    async def autoboard(self, ctx):
        pass

    @autoboard.sub_command(name="create", description="Create server autoposting leaderboards")
    async def setupboard(self, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, autoboard_type: str = commands.Param(choices=["Player Leaderboard", "Clan Leaderboard"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        await ctx.response.defer()
        msg = await ctx.original_message()

        country = None
        if autoboard_type == "Clan Leaderboard":
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
                options.append(disnake.SelectOption(label=f"{country}", value=f"{country}"))

            select1 = disnake.ui.Select(
                options=options,
                placeholder="Page Navigation",
                min_values=1,  # the minimum number of options a user must select
                max_values=1  # the maximum number of options a user can select
            )
            action_row = disnake.ui.ActionRow()
            action_row.append_item(select1)

            embed = disnake.Embed(title="**For what country would you like the leaderboard autoboard?**",
                                  color=disnake.Color.green())

            await ctx.edit_original_message(embed=embed, components=[action_row])

            def check(res: disnake.MessageInteraction):
                return res.message.id == msg.id

            country = False
            while country == False:
                try:
                    res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                              timeout=600)
                except:
                    await msg.edit(components=[])
                    break

                if res.author.id != ctx.author.id:
                    await res.send(content="You must run the command to interact with components.", ephemeral=True)
                    continue

                country = str(res.values[0])



        tex = ""
        if autoboard_type == "Player Leaderboard":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"topboardchannel": channel.id}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"tophour": 5}})
        else:
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbboardChannel": channel.id}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"country": country}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbhour": 5}})
            tex = f"\nCountry: {country}"

        time = f"<t:{1643263200}:t>"
        embed = disnake.Embed(title="**Autoboard Successfully Setup**",
                              description=f"Channel: {channel.mention}\n"
                                          f"Time: {time}\n"
                                          f"Type: {autoboard_type}{tex}",
                              color=disnake.Color.green())
        await msg.edit(embed=embed)



    @autoboard.sub_command(name="remove", description="Remove a server autoboard")
    async def removeboard(self, ctx: disnake.ApplicationCommandInteraction, autoboard_type: str = commands.Param(choices=["Player Leaderboard", "Clan Leaderboard"])):
        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if autoboard_type == "Player Leaderboard":
            await server.update_one({"server": ctx.guild.id}, {'$set': {"topboardchannel": None}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"tophour": None}})
        else:
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbboardChannel": None}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"country": None}})
            await server.update_one({"server": ctx.guild.id}, {'$set': {"lbhour": None}})

        embed = disnake.Embed(description=f"{autoboard_type} autoboard has been removed.",
                              color=disnake.Color.green())
        await ctx.send(embed=embed, components=[])



    @autoboard.sub_command(name="list", description="View server autoboards")
    async def boardlist(self, ctx):
        tbc = None
        th = None
        lbc = None
        lbh = None
        country = None

        results = await server.find_one({"server": ctx.guild.id})

        real_times = []
        start_time = 1643263200
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
            th = real_times[th - 5]
            th = f"<t:1643263200:t>"
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
            lbh = real_times[lbh - 5]
            lbh = f"<t:1643263200:t>"
        except:
            pass

        try:
            country = results.get("country")
        except:
            pass

        embed = disnake.Embed(title="**Autoboard List**",
                              description=f"Player leaderboard Channel: {tbc}\n"
                                    f"Player leaderboard Post Time: {th}\n"
                                    f"Clan leaderboard Channel: {lbc}\n"
                                    f"Clan leaderboard Post Time: {lbh}\n"
                                    f"Clan leaderboard Country: {country}\n",
                              color=disnake.Color.green())
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

                        embed = disnake.Embed(title=f"**Top {limit} {g.name} players**",
                                              description=rText)
                        if g.icon is not None:
                            embed.set_thumbnail(url=g.icon.url)
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

                    embed = disnake.Embed(title=f"{country_names} Top 25 Leaderboard",
                                          description=text,
                                          color=disnake.Color.green())
                    if g.icon is not None:
                        embed.set_thumbnail(url=g.icon.url)
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