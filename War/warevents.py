import coc
import discord
from HelperMethods.clashClient import client, coc_client, getPlayer

from datetime import datetime, timedelta

usafam = client.usafam
server = usafam.server
clans = usafam.clans
war = usafam.war

from discord.ext import commands

class WarEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.war_spin)

    @coc.WarEvents.state()
    async def war_spin(self, old_war, new_war):
        tag = new_war.clan.tag

        one_hour_ping = False
        two_hour_ping = False
        four_hour_ping = False
        eight_hour_ping = False

        results = clans.find({"clan": tag})
        limit = await clans.count_documents(filter={"clan": tag})
        for document in await results.to_list(length=limit):
            one_hour = document.get("one_hour")
            two_hour = document.get("two_hour")
            four_hour = document.get("four_hour")
            eight_hour = document.get("eight_hour")
            if one_hour == True:
                one_hour_ping = True
            if two_hour == True:
                two_hour_ping = True
            if four_hour == True:
                four_hour_ping = True
            if eight_hour == True:
                eight_hour_ping = True


        end_time = new_war.end_time.time


        if one_hour_ping == True:
            end_time = end_time - timedelta(hours=1)
            day = end_time.day
            hour = end_time.hour
            minute = end_time.minute
            await war.insert_one({
                "tag": new_war.clan.tag,
                "day": day,
                "hour": hour,
                "minute": minute
            })
        if two_hour_ping == True:
            end_time = end_time - timedelta(hours=2)
            day = end_time.day
            hour = end_time.hour
            minute = end_time.minute
            await war.insert_one({
                "tag": new_war.clan.tag,
                "day": day,
                "hour": hour,
                "minute": minute
            })
        if four_hour_ping == True:
            end_time = end_time - timedelta(hours=4)
            day = end_time.day
            hour = end_time.hour
            minute = end_time.minute
            await war.insert_one({
                "tag": new_war.clan.tag,
                "day": day,
                "hour": hour,
                "minute": minute
            })
        if eight_hour_ping == True:
            end_time = end_time - timedelta(hours=8)
            day = end_time.day
            hour = end_time.hour
            minute = end_time.minute
            await war.insert_one({
                "tag": new_war.clan.tag,
                "day": day,
                "hour": hour,
                "minute": minute
            })


def setup(bot: commands.Bot):
    bot.add_cog(WarEvents(bot))