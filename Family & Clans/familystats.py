from disnake.ext import commands
import disnake

import coc

from utils.clash import client, getClan, link_client, pingToMember, coc_client
from utils.components import create_components
usafam = client.usafam
clans = usafam.clans

import math
from Dictionaries.thPicDictionary import thDictionary
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹" ]
from utils.search import search_results

class FamilyStats(commands.Cog, name="Family Stats"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="ranked")
    async def rank(self, ctx):
        pass

    @commands.slash_command(name="top", description="Server's player trophy leaderboard")
    async def top(self, ctx: disnake.ApplicationCommandInteraction, limit:int = 100):
        """
            Parameters
            ----------
            limit: number of players to show
        """
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
            return await ctx.send(content=f"Please use a number between 1 - {len(rankings)}.")

        if limit > len(rankings) :
            limit = len(rankings)

        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)
        cum_score = 0
        if limit == 50:
            z = 1
            for r in rankings:
                if z >= 1 and z <=10:
                    cum_score += (ranking[z-1][1])*0.50
                elif z>= 11 and z<=20:
                    cum_score += (ranking[z-1][1])*0.25
                elif z>= 21 and z<=30:
                    cum_score += (ranking[z-1][1])*0.12
                elif z>= 31 and z<=40:
                    cum_score += (ranking[z-1][1])*0.10
                elif z>= 41 and z<=50:
                    cum_score += (ranking[z-1][1])*0.03
                z+=1

        cum_score = int(cum_score)

        cum_score = "{:,}".format(cum_score)

        embeds = []
        length = math.ceil(limit / 50)
        current_page = 0

        for e in range(0, length):

            rText = ''
            max = limit
            if (e+1)*50 < limit:
                max = (e+1)*50
            for x in range(e*50, max):
                #print(ranking[x])
                place = str(x+1) + "."
                place = place.ljust(3)
                rText+= f"\u200e`{place}` \u200e<:trophy:956417881778815016> \u200e{ranking[x][1]} - \u200e{ranking[x][0]} | \u200e{ranking[x][2]}\n"


            embed = disnake.Embed(title=f"**Top {limit} {ctx.guild} players**",
                                  description=rText)
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            if limit == 50:
                embed.set_footer(text=f"Cumulative Trophies would be 🏆{cum_score}")
            embeds.append(embed)

        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            # print(res.custom_id)
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                               components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                               components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)
                return


    @commands.slash_command(name="best", description="Arranges players to create best 5 clans if eos was now")
    async def best(self, ctx: disnake.ApplicationCommandInteraction):
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

        if l == 0:
            return await ctx.send(content=f"No clans linked to server.")


        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)


        max_clans = math.floor(len(ranking)/50)
        if max_clans > 5:
            max_clans = 5
        text = ""
        clan_num = 0
        for y in range(clan_num, max_clans):
            cum_score = 0
            z = 1
            tt = ranking[(50*y):((50*y)+50)]
            for r in tt:
                if z >= 1 and z <= 10:
                    cum_score += (r[1]) * 0.50
                elif z >= 11 and z <= 20:
                    cum_score += (r[1]) * 0.25
                elif z >= 21 and z <= 30:
                    cum_score += (r[1]) * 0.12
                elif z >= 31 and z <= 40:
                    cum_score += (r[1]) * 0.10
                elif z >= 41 and z <= 50:
                    cum_score += (r[1]) * 0.03
                z += 1

            cum_score = int(cum_score)
            cum_score = "{:,}".format(cum_score)
            text+=f"Clan #{y+1}: 🏆{cum_score}\n"

        embed = disnake.Embed(title=f"Best Possible EOS for {ctx.guild.name}",
            description=text,
            color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="All Clans have 50 Members")
        await ctx.send(embed=embed)


    @commands.slash_command(name="rank", description="Ranks for player")
    async def srank(self, ctx: disnake.ApplicationCommandInteraction, tag_or_user=None):
        """
            Parameters
            ----------
            tag_or_user: Player tag or discord user to search for
        """

        if tag_or_user is None:
            tag_or_user = str(ctx.author.id)

        await ctx.response.defer()
        results = await search_results(ctx, tag_or_user)
        if results == []:
            return await ctx.edit_original_message(content="No results were found.")

        rr = {}
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            clan = await getClan(tag)
            for player in clan.members:
                try:
                    rr[player.tag] = player.trophies
                except:
                    continue

        sorted(rr, key=rr.get, reverse=True)
        rr = {key: rank for rank, key in enumerate(sorted(rr, key=rr.get, reverse=True), 1)}

        embeds = []

        def index_2d(myList, v):
            for i, x in enumerate(myList):
                if v in x:
                    return i
            return None

        disnakeID = await link_client.get_link(results[0])
        member = await pingToMember(ctx, str(disnakeID))

        async for player in coc_client.get_players(results):
            result = player.tag
            from BackgroundLoops.leaderboards import rankingsC
            guildranking = None
            try:
                guildranking = rr[player.tag]
            except:
                pass
            if guildranking == None:
                guildranking = f"<:status_offline:910938138984206347>"
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
                embed = disnake.Embed(title=f"**Ranks for {member.display_name}**",
                    description=f"Name: {player.name}\n" +
                                f"Tag: {player.tag}\n" +
                                f"Clan: {clan}\n" +
                                f"Trophies: {player.trophies}\n"
                                f"{ctx.guild.name} : {guildranking}\n"
                                f"Rank: <a:earth:861321402909327370> {gspot} | {flag} {cou_spot}\n"+ country_name,
                    color=disnake.Color.green())
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed = disnake.Embed(title=f"**Ranks for {player.name}**",
                                      description=f"Name: {player.name}\n" +
                                                  f"Tag: {player.tag}\n" +
                                                  f"Clan: {clan}\n" +
                                                  f"Trophies: {player.trophies}\n"
                                                  f"{ctx.guild.name} : {guildranking}\n"
                                                  f"Rank: <a:earth:861321402909327370> {gspot} | {flag} {cou_spot}\n" + country_name,
                                      color=disnake.Color.green())
                if player.town_hall >= 4:
                    embed.set_thumbnail(url=thDictionary(player.town_hall))

            embeds.append(embed)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds))

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            # print(res.custom_id)
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                               components=create_components(current_page, embeds))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                               components=create_components(current_page, embeds))

    
    @rank.sub_command(name="players", description="Region rankings for players on server")
    async def prank(self, ctx: disnake.ApplicationCommandInteraction):
        server_players = {}
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            clan = await getClan(tag)
            for player in clan.members:
                try:
                    server_players[player.tag] = player.trophies
                except:
                    continue

        sorted(server_players, key=server_players.get, reverse=True)
        server_players = {key: rank for rank, key in enumerate(sorted(server_players, key=server_players.get, reverse=True), 1)}
        server_players = list(server_players.keys())
        from BackgroundLoops.leaderboards import glob_dict, country_dict

        embeds = []
        num = 0
        text = ""
        #[loc, rank, country, clantag, clanname, trophies, playername]
        for tag in server_players:
            glob_rank_player = None
            country_rank_player = None
            try:
                glob_rank_player = glob_dict[tag]
            except:
                pass
            try:
                country_rank_player = country_dict[tag]
            except:
                pass
            if glob_rank_player is None and country_rank_player is None:
                continue

            if glob_rank_player is not None:
                num += 1
                rank = str(glob_rank_player[1]).ljust(3)
                text += f"<:trophy:956417881778815016>`{glob_rank_player[5]}` | <a:earth:861321402909327370> `{rank}` | {glob_rank_player[6]}\n"

            if country_rank_player is not None:
                num += 1
                rank = str(country_rank_player[1]).ljust(3)
                text += f"<:trophy:956417881778815016>`{country_rank_player[5]}` | :flag_{country_rank_player[0].lower()}: `{rank}` | {country_rank_player[6]} | {country_rank_player[2]}\n"

            if num == 25:
                embed = disnake.Embed(title=f"**{ctx.guild.name} Player Country LB Rankings**", description=text)
                embeds.append(embed)
                num = 0
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"**{ctx.guild.name} Player Country LB Rankings**", description=text)
            embeds.append(embed)

        if embeds == []:
            return await ctx.send("No ranked players on this server.")
        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)


    @rank.sub_command(name="clans", description="Region rankings for clans on server")
    async def crank(self, ctx):

        server_clans = []
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            server_clans.append(tag)

        from BackgroundLoops.leaderboards import clan_glob_dict, clan_country_dict

        num = 0
        text = ""
        for tag in server_clans:
            glob_rank_clan = None
            country_rank_clan = None
            try:
                glob_rank_clan = clan_glob_dict[tag]
            except:
                pass
            try:
                country_rank_clan = clan_country_dict[tag]
            except:
                pass
            if glob_rank_clan is None and country_rank_clan is None:
                continue

            if glob_rank_clan is not None:
                num += 1
                rank = str(glob_rank_clan[0]).ljust(3)
                text += f"<a:earth:861321402909327370> `{rank}` | {glob_rank_clan[1]}\n"

            if country_rank_clan is not None:
                num += 1
                rank = str(country_rank_clan[0]).ljust(3)
                text += f":flag_{country_rank_clan[3].lower()}: `{rank}` | {country_rank_clan[1]} | {country_rank_clan[2]}\n"

        if text == "":
            text = "No ranked clans"
        embed = disnake.Embed(title=f"**{ctx.guild.name} Clan Country Rankings (Top 200)**",
                              description=text,
                              color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        await ctx.send(embed=embed)


    async def autocomp_names(self, query: str):
        locations = await coc_client.search_locations()
        results = []
        if query.lower() in "Global":
            results.append("Global")
        for location in locations:
            if query.lower() in location.name.lower():
                ignored = ["Africa", "Europe", "North America", "South America", "Asia"]
                if location.name not in ignored:
                    if location.name not in results:
                        results.append(location.name)
        return results[0:25]

    @commands.slash_command(name="leaderboard")
    async def leaderboard(self, ctx):
        pass

    @leaderboard.sub_command(name="clan", description="Clan leaderboard of a location")
    async def clan_leaderboards(self, ctx: disnake.ApplicationCommandInteraction, country: str = commands.Param(autocomplete=autocomp_names)):
        """
            Parameters
            ----------
            country: country to fetch leaderboard for
        """
        tags = []
        tracked = clans.find({"server": ctx.guild.id})
        limit = await clans.count_documents(filter={"server": ctx.guild.id})
        if limit == 0:
            return await ctx.send("No clans linked to this server.")
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            tags.append(tag)




        if country != "Global":
            locations = await coc_client.search_locations(limit=None)
            is_country = (country != "International")
            country = coc.utils.get(locations, name=country, is_country=is_country)
            country_names = country.name
            rankings = await coc_client.get_location_clans(location_id=country.id)
        else:
            rankings = await coc_client.get_location_clans()
            country_names = "Global"

        x = 0
        embeds = []
        text = ""
        for clan in rankings:
            rank = str(x+1)
            rank = rank.ljust(2)
            star = ""
            if clan.tag in tags:
                star = "⭐"
            text += f"`\u200e{rank}`🏆`\u200e{clan.points}` \u200e{clan.name}{star}\n"
            x += 1
            if x != 0 and x%50 == 0:
                embed = disnake.Embed(title=f"{country_names} Top 50 Leaderboard",
                                      description=text,
                                      color=disnake.Color.green())
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"{country_names} Top 50 Leaderboard",
                                  description=text,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)




def setup(bot: commands.Bot):
    bot.add_cog(FamilyStats(bot))