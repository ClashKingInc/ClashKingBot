
from disnake.ext import commands, tasks
from utils.clash import client, getClan, coc_client
import coc
import disnake
import datetime as dt
import math

usafam = client.usafam
clans = usafam.clans
server = usafam.server


class board_loop(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.board_check.start()

    def cog_unload(self):
        self.board_check.cancel()

    @tasks.loop(seconds=60)
    async def board_check(self):
        try:
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
        except:
            pass

    @board_check.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(board_loop(bot))