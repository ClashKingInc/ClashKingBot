from discord.ext import commands
import discord

import coc

from discord_slash.utils.manage_components import create_button, wait_for_component, create_select, create_select_option, create_actionrow
from discord_slash.model import ButtonStyle

from HelperMethods.clashClient import client, getClan, link_client, pingToMember, getPlayer, coc_client
usafam = client.usafam
clans = usafam.clans

import math
from Dictionaries.thPicDictionary import thDictionary


class top(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        #self.lb_update.start()


    @commands.command(name="top")
    async def top(self, ctx, *, limit = 100):
        rankings = []
        tracked = clans.find({"server": ctx.guild.id})
        l = await clans.count_documents(filter={"server": ctx.guild.id})
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

        if limit < 1 :
            return await ctx.send(content=f"Please use a number between 1 - {len(rankings)}.", embed=None)

        if limit > len(rankings) :
            limit = len(rankings)
        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)

        embeds = []
        length = math.ceil(limit / 25)
        current_page = 0

        for e in range(0, length):

            rText = ''
            max = limit
            if (e+1)*25 < limit:
                max = (e+1)*25
            for x in range(e*25, max):
                #print(ranking[x])
                place = str(x+1) + "."
                place = place.ljust(3)
                rText+= f"\u200e`{place}` \u200e<:a_cups:667119203744088094> \u200e{ranking[x][1]} - \u200e{ranking[x][0]} | \u200e{ranking[x][2]}\n"


            embed = discord.Embed(title=f"**Top {limit} {ctx.guild} players**",
                                  description=rText)
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embeds.append(embed)

        msg = await ctx.send(embed=embeds[0], components=self.create_components(current_page, limit), mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)
                return


    @commands.command(name="rank")
    async def rank(self, ctx, *, search_query=None):
        if search_query == None:
            search_query = str(ctx.author.id)
        embed = discord.Embed(
            description="<a:loading:884400064313819146> Fetching Stats. | Can take 10-15 seconds.",
            color=discord.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        search = self.bot.get_cog("search")
        results = await search.search_results(ctx, search_query)
        if results == []:
            return await msg.edit(content="No results were found.", embed=None)

        rr = []
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            clan = await getClan(tag)
            for player in clan.members:
                try:
                    playerStats = []
                    playerStats.append(player.name)
                    playerStats.append(player.trophies)
                    playerStats.append(player.clan.name)
                    playerStats.append(player.tag)
                    rr.append(playerStats)
                except:
                    continue

        ranking = sorted(rr, key=lambda l: l[1], reverse=True)

        embeds = []

        def index_2d(myList, v):
            for i, x in enumerate(myList):
                if v in x:
                    return i
            return None

        for result in results:
            discordID = await link_client.get_link(result)
            member = await pingToMember(ctx, str(discordID))
            player = await getPlayer(result)
            result = player.tag
            from Boards.leaderboards import rankingsC
            usaranking = index_2d(ranking, result)
            try:
                usaranking = usaranking + 1
            except:
                pass
            if usaranking == None:
                usaranking = f"<:status_offline:910938138984206347>"
            gspot = "<:status_offline:910938138984206347>"
            cou_spot = "<:status_offline:910938138984206347>"
            flag = "🏳️"
            country_name = "Country: Not Ranked\n"

            spots = [i for i, value in enumerate(rankingsC) if value == result]
            #print(rankingsC)
            for r in spots:
                loc = rankingsC[r + 1]
                if loc == "global":
                    gspot = rankingsC[r + 2]
                else:
                    cou_spot = rankingsC[r + 2]
                    loc = loc.lower()
                    flag = f":flag_{loc}:"
                    country_name = "Country: " + rankingsC[r + 3] + "\n"

            clan = ""
            try:
                #clanlink = player.clan.share_link
                clan = player.clan.name
                clan = f"{clan}"
            except:
                clan = "None"

            if member != None:
                embed = discord.Embed(title=f"**Ranks for {member.display_name}**",
                    description=f"Name: {player.name}\n" +
                                f"Tag: {player.tag}\n" +
                                f"Clan: {clan}\n" +
                                f"Trophies: {player.trophies}\n"
                                f"{ctx.guild.name} : {usaranking}\n"
                                f"Rank: <a:earth:861321402909327370> {gspot} | {flag} {cou_spot}\n"+ country_name,
                    color=discord.Color.green())
                embed.set_thumbnail(url=member.avatar_url)
            else:
                embed = discord.Embed(title=f"**Ranks for {player.name}**",
                                      description=f"Name: {player.name}\n" +
                                                  f"Tag: {player.tag}\n" +
                                                  f"Clan: {clan}\n" +
                                                  f"Trophies: {player.trophies}\n"
                                                  f"{ctx.guild.name} : {usaranking}\n"
                                                  f"Rank: <a:earth:861321402909327370> {gspot} | {flag} {cou_spot}\n" + country_name,
                                      color=discord.Color.green())
                embed.set_thumbnail(url=thDictionary(player.town_hall))

            embeds.append(embed)

        current_page = 0
        limit = len(embeds) * 25
        await msg.edit(embed=embeds[0], components=self.create_components(current_page, limit),
                             mention_author=False)

        while True:
            try:
                res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()

            # print(res.custom_id)
            if res.custom_id == "Previous":
                current_page -= 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))

            elif res.custom_id == "Next":
                current_page += 1
                await msg.edit(embed=embeds[current_page],
                               components=self.create_components(current_page, limit))



    @commands.command(name="prank")
    async def prank(self, ctx):
        master_num = 0
        if ctx.guild.id == 328997757048324101:
            master_num = 1

        rr = []
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            rr.append(tag)

        from Boards.leaderboards import rankingsC

        countries = []
        text = ""
        prev_country = None
        country = None
        embeds = []
        num = 0

        #[tag, loc, rank, country, clantag, clanname, trophies, playername]
        y = 0
        for x in rankingsC:
            y += 1
            if x in rr:
                #print(f"{rankingsC[y -5]},{rankingsC[y -4]},{rankingsC[y -3]},{rankingsC[y -2]}, {rankingsC[y -1]}, {rankingsC[y]}, {rankingsC[y +1]}, {rankingsC[y +2]}")
                loc = rankingsC[y -4]
                loc = loc.lower()
                rank = rankingsC[y - 3]
                rank = str(rank)
                name = rankingsC[y + 2]
                trophies = rankingsC[y + 1]
                clanname = rankingsC[y]

                if loc == "global":
                    country = "Global"
                else:
                    country = rankingsC[y-2]

                num += 1

                if prev_country == None:
                    prev_country = country

                if prev_country != country:
                    if num <= master_num:
                        num = 0
                        prev_country = country
                        text = ""
                    else:
                        embed = discord.Embed(title=f"**{ctx.guild.name} Rankings | {prev_country}**",
                                              description=text,
                                              color=discord.Color.green())
                        embed.set_thumbnail(url=ctx.guild.icon_url_as())
                        text = ""
                        countries.append(prev_country)
                        # print(prev_country)
                        prev_country = country
                        embeds.append(embed)
                        num = 0

                rank = rank.rjust(3)
                if loc != "global":
                    flag = f":flag_{loc}:"
                else:
                    flag = "<a:earth:861321402909327370>"
                text += f"`🏆{trophies}`{flag}`{rank}` **{name}** [{clanname}]\n"

        if num > master_num:
            embed = discord.Embed(title=f"**{ctx.guild.name} Rankings | {country}**",
                                  description=text,
                                  color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embeds.append(embed)
            countries.append(country)

        if prev_country == None:
            embed = discord.Embed(title=f"**{ctx.guild.name} Rankings **",
                                  description="No ranked players.",
                                  color=discord.Color.green())
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embeds.append(embed)


        num_countries = len(countries)
        if num_countries > 25:
            current_page = 0
            limit = len(embeds) * 25
            msg = await ctx.send(embed=embeds[0], components=self.create_components(current_page, limit),
                           mention_author=False)

            while True:
                try:
                    res = await wait_for_component(self.bot, components=self.create_components(current_page, limit),
                                                   messages=msg, timeout=600)
                except:
                    await msg.edit(components=[])
                    break

                if res.author_id != ctx.author.id:
                    await res.send(content="You must run the command to interact with components.", hidden=True)
                    continue

                await res.edit_origin()

                # print(res.custom_id)
                if res.custom_id == "Previous":
                    current_page -= 1
                    await msg.edit(embed=embeds[current_page],
                                   components=self.create_components(current_page, limit))

                elif res.custom_id == "Next":
                    current_page += 1
                    await msg.edit(embed=embeds[current_page],
                                   components=self.create_components(current_page, limit))
        else:
            options = []
            for country in countries:
                options.append(create_select_option(label=f"{country}", value=f"{country}"))

            select1 = create_select(
                options=options,
                placeholder="Choose location",
                min_values=1,  # the minimum number of options a user must select
                max_values=1  # the maximum number of options a user can select
            )
            action_row = create_actionrow(select1)

            msg = await ctx.send(embed=embeds[0], components=[action_row])

            while True:
                try:
                    res = await wait_for_component(self.bot, components=action_row,
                                                   messages=msg, timeout=600)
                except:
                    await msg.edit(components=[])
                    break

                if res.author_id != ctx.author.id:
                    await res.send(content="You must run the command to interact with components.", hidden=True)
                    continue

                await res.edit_origin()
                value = res.values[0]

                current_page = countries.index(value)

                await msg.edit(embed=embeds[current_page],
                               components=[action_row])

    @commands.command(name="crank")
    async def crank(self, ctx):

        rr = []
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            rr.append(tag)

        global_rank = ""

        glob = await coc_client.get_location_clans()
        x=0
        for clan in glob:
            x+=1
            if clan.tag in rr:
                global_rank += f"{clan.name}: {x}\n"

        us_rank = ""
        x=0
        clan_list = await coc_client.get_location_clans(location_id=32000249)
        for clan in clan_list:
            x+=1
            if clan.tag in rr:
                us_rank += f"{clan.name}: {x}\n"

        full_rank = ""
        if global_rank != "":
            full_rank += f"**Global Rankings**\n{global_rank}\n"
        if us_rank != "":
            full_rank += f"**United States Rankings**\n{us_rank}\n\n"

        if full_rank == "":
            full_rank = "No ranked clans."



        embed = discord.Embed(title=f"**{ctx.guild.name} Clan Rankings (Top 200)**",
                              description=full_rank,
                              color=discord.Color.green())
        embed.set_thumbnail(url=ctx.guild.icon_url_as())

        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderb(self, ctx):

        rr = []
        tags = []
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            tags.append(tag)
            c = await getClan(tag)
            location = str(c.location)
            if location not in rr:
                rr.append(str(location))
                #print(location)


        embeds = []
        for location in rr:
            text = ""
            locations = await coc_client.search_locations(limit=None)
            is_country = (location != "International")
            country = coc.utils.get(locations, name=location, is_country=is_country)
            country_names = country.name
            #print(country.id)
            rankings = await coc_client.get_location_clans(location_id=country.id)
            #print(rankings)

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
            embed.set_thumbnail(url=ctx.guild.icon_url_as())
            embeds.append(embed)

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

        msg = await ctx.send(embed=embeds[0], components=[action_row])

        while True:
            try:
                res = await wait_for_component(self.bot, components=action_row,
                                               messages=msg, timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.author_id != ctx.author.id:
                await res.send(content="You must run the command to interact with components.", hidden=True)
                continue

            await res.edit_origin()
            value = res.values[0]

            current_page = rr.index(value)

            await msg.edit(embed=embeds[current_page],
                           components=[action_row])



    def create_components(self, current_page, limit):
        length = math.ceil(limit/25)
        if length == 1:
            return []

        page_buttons = [create_button(label="", emoji="◀️", style=ButtonStyle.blue, disabled=(current_page == 0),
                                      custom_id="Previous"),
                        create_button(label=f"Page {current_page + 1}/{length}", style=ButtonStyle.grey,
                                      disabled=True),
                        create_button(label="", emoji="▶️", style=ButtonStyle.blue,
                                      disabled=(current_page == length - 1), custom_id="Next"),
                        create_button(label="", emoji="🖨️", style=ButtonStyle.grey,
                                      custom_id="Print")
                        ]
        page_buttons = create_actionrow(*page_buttons)

        return [page_buttons]






def setup(bot: commands.Bot):
    bot.add_cog(top(bot))