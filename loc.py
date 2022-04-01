from discord.ext import commands, tasks
from utils.clashClient import coc_client
import aiohttp
from discord import Webhook, AsyncWebhookAdapter
import motor.motor_asyncio
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://45.33.3.218:27017/admin?readPreference=primary&appname=MongoDB%20Compass&directConnection=true&ssl=false")
legends_stats = client.legends_stats
ongoing_stats = legends_stats.ongoing_stats
from matplotlib import pyplot as plt
import io
import numpy as np
import discord
from coc import utils
import pytz
utc = pytz.utc
from datetime import datetime


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

        embed = discord.Embed(title=f"Best fit line of {num_p} defenses\n"
                                    f"Equation: {str(theta[0])[1:6]}x {int(theta[1])}",
                              color=discord.Color.blue())
        file = discord.File(fp=buf, filename="filename.png")
        pic_channel = await self.bot.fetch_channel(884951195406458900)
        msg = await pic_channel.send(file=file)
        pic = msg.attachments[0].url
        embed.set_image(url=pic)
        plt.clf()
        plt.close("all")
        await ctx.send(embed=embed)

    @commands.command(name="legendfix")
    @commands.is_owner()
    async def test(self, ctx):
        tracked = ongoing_stats.find()
        # await ongoing_stats.create_index([("tag", 1)], unique = True)

        limit = await ongoing_stats.count_documents(filter={})
        # print(f"Loop 1 size {limit}")
        for document in await tracked.to_list(length=limit):
            tag = document.get("tag")
            await ongoing_stats.update_one({'tag': f"{tag}"},
                                           {'$set': {'today_defenses': []}})

        await ctx.send("Today's defenses removed.")






def setup(bot: commands.Bot):
    bot.add_cog(loc(bot))