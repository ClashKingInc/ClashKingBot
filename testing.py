from disnake.ext import commands, tasks
from utils.clash import coc_client
from matplotlib import pyplot as plt
import io
import numpy as np
import disnake
from coc import utils
import pytz
utc = pytz.utc
from datetime import datetime
import calendar
import csv
from collections import defaultdict
from utils.components import create_components
import motor.motor_asyncio
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://45.33.3.218:27017/admin?readPreference=primary&appname=MongoDB%20Compass&directConnection=true&ssl=false")
legends_stats = client.legends_stats
ongoing_stats = legends_stats.ongoing_stats
profile_db = legends_stats.profile_db


from dbplayer import DB_Player

from utils.clash import client as client2, getClan, link_client
usafam = client2.usafam
clans = usafam.clans
temp = usafam.temp

class loc(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="test2")
    async def test2(self, ctx):
        points = []
        tracked = ongoing_stats.find()
        limit = await ongoing_stats.count_documents(filter={})
        for document in await tracked.to_list(length=limit):
            previous_defs = document.get("previous_defenses")
            tag = document.get("tag")
            if len(previous_defs) == 0:
                continue
            previous_defs = previous_defs[:-1]
            previous_hits = document.get("previous_hits")
            previous_hits = previous_hits[:-1]
            await ongoing_stats.update_one({'tag': f"{tag}"},
                                           {'$set': {"previous_hits": previous_hits,
                                                      "previous_defenses": previous_defs}})



        await ctx.send("done")
        '''   
            end_of_days = document.get("end_of_day")
            previous_defs = previous_defs[:-2]
            end_of_days = end_of_days[:-1]
            end_of_days = end_of_days[1:]
            for (defs, day) in zip(previous_defs, end_of_days):
                #if day < 5000:
                    #continue
                if defs == []:
                    continue
                if sum(defs) > 320:
                    continue
                #if len(defs) <= 7:
                   #continue
                day = int(day)
                p = [day, sum(defs)]
                points.append(p)

        num_p = len(points)
        points = np.asarray(points)
        x = points[:, 0].reshape(points.shape[0], 1)
        X = np.append(x, np.ones((points.shape[0], 1)), axis=1)
        y = points[:, 1].reshape(points.shape[0], 1)

        # Calculating the parameters using the least square method
        theta = np.linalg.inv(X.T.dot(X)).dot(X.T).dot(y)

        print(f'The parameters of the line: {theta}')

        # Now, calculating the y-axis values against x-values according to
        # the parameters theta0 and theta1
        y_line = X.dot(theta)

        # Plotting the data points and the best fit line
        plt.scatter(x, y, marker=".", s=20)
        plt.plot(x, y_line, 'r')
        plt.title(f"Best fit line of {num_p} defenses\n"
                                    f"Equation: {str(theta[0])[1:6]}x {int(theta[1])}")
        plt.xlabel('x-axis')
        plt.ylabel('y-axis')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        embed = disnake.Embed(title=f"Best fit line of {num_p} defenses\n"
                                    f"Equation: {str(theta[0])[1:6]}x {int(theta[1])}",
                              color=disnake.Color.blue())
        file = disnake.File(fp=buf, filename="filename.png")
        pic_channel = await self.bot.fetch_channel(884951195406458900)
        msg = await pic_channel.send(file=file)
        pic = msg.attachments[0].url
        embed.set_image(url=pic)
        plt.clf()
        plt.close("all")
        await ctx.send(embed=embed)
        '''

    @commands.command(name="test")
    @commands.is_owner()
    async def test(self, ctx):
        await ongoing_stats.update_many({"new_change": {"$ne": []}},
                               {'$set': {'new_change': []}})
        await ctx.send("done")

    @commands.command(name="daily_list")
    @commands.is_owner()
    async def daily(self, ctx, id):
        results = await profile_db.find_one({'discord_id': int(id)})
        if results is None:
            return await ctx.send([])
        tags = results.get("profile_tags")
        await ctx.send(tags)

    @commands.command(name="countries")
    async def countries(self, ctx, tag=None):
        r_name = ""
        tags = []
        if tag is None:
            tracked = clans.find({"server": ctx.guild.id})
            limit = await clans.count_documents(filter={"server": ctx.guild.id})
            if limit == 0:
                return await ctx.send("This server has no linked clans.")
            for tClan in await tracked.to_list(length=limit):
                tag = tClan.get("tag")
                tags.append(tag)

            r_name = ctx.guild.name
        else:
            clan = await getClan(tag)
            if clan is None:
                return await ctx.send("invalid clan tag")
            tags.append(clan.tag)
            r_name = clan.name

        embeds = []
        members = []
        ptags = []
        async for clan in coc_client.get_clans(tags):
            for member in clan.members:
                members.append(member)
                ptags.append(member.tag)

        num = 0
        text = ""
        results = ongoing_stats.find({"tag": {"$in": ptags}}).sort("location")
        limit = await ongoing_stats.count_documents(filter={"tag": {"$in": ptags}})
        for result in await results.to_list(length=limit):
            player = DB_Player(result)
            location = player.location
            if location is None:
                continue
            location_code = player.location_code
            flag = f":flag_{location_code.lower()}:"
            name = player.name
            text+= f"\u200e{name} - \u200e{flag}{location}\n"
            num+=1
            if num == 25:
                embed = disnake.Embed(title=f"**{r_name} Player Country List**", description=text)
                embeds.append(embed)
                num = 0
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"**{r_name} Player Country List**", description=text)
            embeds.append(embed)

        if embeds == []:
            return await ctx.send("No player locations for this server.")
        current_page = 0
        msg = await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))

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

    @commands.command(name="trop")
    async def tro(self, ctx, tag):
        player = await coc_client.get_player(tag)
        gspot = player.legend_statistics.previous_season.trophies
        await ctx.send(f"{player.name} - {gspot}")

    @commands.command(name="create")
    @commands.is_owner()
    async def create(self, ctx):
        # current season start date
        # use to get previous season (month - 1)
        # end of last season is beginning of current
        end = utils.get_season_start().replace(tzinfo=utc).date()
        start = utils.get_season_start(month=end.month - 1, year=end.year).replace(tzinfo=utc).date()
        month = calendar.month_name[start.month + 1]
        length_of_season = end - start
        length_of_season = length_of_season.days

        # get the first record we need
        # get length progressed in current season
        now = datetime.utcnow().replace(tzinfo=utc).date()
        now_ = datetime.utcnow().replace(tzinfo=utc)
        current_season_progress = now - end
        current_season_progress = current_season_progress.days
        if now_.hour <= 5:
            current_season_progress -= 1

        first_record = current_season_progress
        last_record = first_record + length_of_season

        clan_names = []
        tracked = clans.find({"server": 810466565744230410})
        limit = await clans.count_documents(filter={"server": 810466565744230410})
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            clan_names.append(name)

        f = ["Name"]
        for x in range(1, 29):
            f.append(f"Day {x}")
        lb = [f]

        rankings = []
        tracked = ongoing_stats.find()
        #first_record+=1
        limit = await ongoing_stats.count_documents(filter={})
        for document in await tracked.to_list(length=limit):
            end_of_days = document.get("end_of_day")
            clan = document.get("clan")
            if clan not in clan_names:
                continue
            len_y = len(end_of_days)
            name = document.get("name")
            tag = document.get("tag")
            if first_record-1 >= len_y - 2:
                continue
            #day = end_of_days[-first_record]
            eod = end_of_days[len(end_of_days) - last_record:len(end_of_days) - first_record]
            if len(eod) <= 26:
                continue
            eod.insert(0, 5000)
            eod.insert(0, name)
            rankings.append(eod)

        ranking = sorted(rankings, key=lambda l: l[29], reverse=True)
        ranking = ranking[0:25]

        lb = lb + ranking

        print("here3")
        with open("lb6.csv", "w", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(lb)

        await ctx.send("done")

    @commands.command(name="addtags")
    @commands.is_owner()
    async def addtags(self, ctx):
        tracked = temp.find()
        limit = await temp.count_documents(filter={})
        for document in await tracked.to_list(length=limit):
            tags = [document.get("tag")]
            alts = document.get("alttags")
            discordID = int(document.get("discordtag"))
            for alt in alts:
                alttag = alt.get("alttag")
                tags.append(alttag)

            for tag in tags:
                link = await link_client.get_link(tag)
                if link is None:
                    await link_client.add_link(player_tag=tag, discord_id=discordID)
                else:
                    continue

        await ctx.send("done")





def setup(bot: commands.Bot):
    bot.add_cog(loc(bot))