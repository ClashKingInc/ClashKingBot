from disnake.ext import commands
import disnake
from utils.search import search_results
from utils.components import create_components
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import LegendRanking
import math
from Dictionaries.thPicDictionary import thDictionary
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹" ]


class FamilyStats(commands.Cog, name="Family Trophy Stats"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="ranked")
    async def rank(self, ctx):
        pass

    @commands.slash_command(name="best", description="Arranges players to create best 5 clans if eos was now")
    async def best(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        rankings = []
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        l = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=l):
            tag = clan.get("tag")
            clan = await self.bot.getClan(tag)
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
        await ctx.edit_original_message(embed=embed)


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
        results = await search_results(self.bot, tag_or_user)
        if results == []:
            return await ctx.edit_original_message(content="No results were found.")

        rr = {}
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            clan = await self.bot.getClan(tag)
            for player in clan.members:
                try:
                    rr[player.tag] = player.trophies
                except:
                    continue

        sorted(rr, key=rr.get, reverse=True)
        rr = {key: rank for rank, key in enumerate(sorted(rr, key=rr.get, reverse=True), 1)}

        embeds = []

        disnakeID = await self.bot.link_client.get_link(results[0])
        member = await self.bot.pingToMember(ctx, str(disnakeID))

        async for player in self.bot.coc_client.get_players(results):
            result_ranking = await self.bot.leaderboard_db.find_one({"tag": player.tag})
            ranking = LegendRanking(result_ranking)

            guildranking = None
            try:
                guildranking = rr[player.tag]
            except:
                pass
            if guildranking is None:
                guildranking = f"<:status_offline:910938138984206347>"


            try:
                clan = player.clan.name
                clan = f"{clan}"
            except:
                clan = "None"

            if member is not None:
                embed = disnake.Embed(title=f"**Ranks for {member.display_name}**",
                    description=f"Name: {player.name}\n" +
                                f"Tag: {player.tag}\n" +
                                f"Clan: {clan}\n" +
                                f"Trophies: {player.trophies}\n"
                                f"{ctx.guild.name} : {guildranking}\n"
                                f"Rank: <a:earth:861321402909327370> {ranking.global_ranking} | {ranking.flag} {ranking.local_ranking}\n"+ f"Country: {ranking.country}",
                    color=disnake.Color.green())
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed = disnake.Embed(title=f"**Ranks for {player.name}**",
                                      description=f"Name: {player.name}\n" +
                                                  f"Tag: {player.tag}\n" +
                                                  f"Clan: {clan}\n" +
                                                  f"Trophies: {player.trophies}\n"
                                                  f"{ctx.guild.name} : {guildranking}\n"
                                                  f"Rank: <a:earth:861321402909327370> {ranking.global_ranking} | {ranking.flag} {ranking.local_ranking}\n" + f"Country: {ranking.country}",
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
        await ctx.response.defer()
        server_players = {}
        names = {}
        trophies = {}
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        tags = []
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            tags.append(tag)

        async for clan in self.bot.coc_client.get_clans(tags):
            for player in clan.members:
                try:
                    server_players[player.tag] = player.trophies
                    trophies[player.tag] = player.trophies
                    names[player.tag] = player.name
                except:
                    continue

        sorted(server_players, key=server_players.get, reverse=True)
        server_players = {key: rank for rank, key in enumerate(sorted(server_players, key=server_players.get, reverse=True), 1)}
        server_players_list = list(server_players.keys())

        embeds = []
        num = 0
        text = ""
        #[loc, rank, country, clantag, clanname, trophies, playername]
        for tag in server_players_list:
            result_ranking = await self.bot.leaderboard_db.find_one({"tag": tag})
            ranking = LegendRanking(result_ranking)
            if ranking.global_ranking != "<:status_offline:910938138984206347>":
                num += 1
                text += f"<:trophy:956417881778815016>`{trophies[tag]}` | <a:earth:861321402909327370> `{ranking.global_ranking}` | {names[tag]}\n"

            if ranking.local_ranking != "<:status_offline:910938138984206347>":
                num += 1
                text += f"<:trophy:956417881778815016>`{trophies[tag]}` | {ranking.flag} {ranking.country} | {names[tag]}\n"

            if num == 25:
                embed = disnake.Embed(title=f"**{ctx.guild.name} Player Country LB Rankings**", description=text)
                embeds.append(embed)
                num = 0
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"**{ctx.guild.name} Player Country LB Rankings**", description=text)
            embeds.append(embed)

        if embeds == []:
            return await ctx.edit_original_message(content="No ranked players on this server.")
        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
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
                await res.edit_original_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.edit_original_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)


    @rank.sub_command(name="clans", description="Region rankings for clans on server")
    async def crank(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        server_clans = []
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            server_clans.append(tag)

        num = 0
        text = ""
        for tag in server_clans:
            result_ranking = await self.bot.clan_leaderboard_db.find_one({"tag": tag})
            ranking = LegendRanking(result_ranking)

            clan = None
            if ranking.global_ranking != "<:status_offline:910938138984206347>":
                num += 1
                clan = await self.bot.getClan(tag)
                text += f"<a:earth:861321402909327370> `{ranking.global_ranking}` | {clan.name}\n"

            if ranking.local_ranking != "<:status_offline:910938138984206347>":
                num += 1
                if clan is None:
                    clan = await self.bot.getClan(tag)
                text += f"{ranking.flag} `{ranking.local_ranking}` | {ranking.country} | {clan.name}\n"

        if text == "":
            text = "No ranked clans"
        embed = disnake.Embed(title=f"**{ctx.guild.name} Clan Country Rankings (Top 200)**",
                              description=text,
                              color=disnake.Color.green())
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        await ctx.edit_original_message(embed=embed)



def setup(bot: CustomClient):
    bot.add_cog(FamilyStats(bot))