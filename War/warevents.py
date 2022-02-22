import coc
import discord
from HelperMethods.clashClient import client, coc_client, getPlayer

from datetime import datetime, timedelta

usafam = client.usafam
server = usafam.server
clans = usafam.clans
war = usafam.war

import pytz
tiz = pytz.utc

from discord.ext import commands

class WarEvents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        coc_client.add_events(self.war_spin)

    @coc.WarEvents.state()
    async def war_spin(self, old_war, new_war : coc.ClanWar):
        
        tag = new_war.clan.tag
        length = new_war.end_time.seconds_until

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

        end_time = new_war.end_time.time.replace(tzinfo=tiz).timestamp()

        if length < 4000:
            one_hour_ping = False
            two_hour_ping = False
            four_hour_ping = False
            eight_hour_ping = False
        elif length <= 7200:
            two_hour_ping = False
            four_hour_ping = False
            eight_hour_ping = False
        elif length <= 14400:
            four_hour_ping = False
            eight_hour_ping = False
        elif length <= 14400:
            eight_hour_ping = False

        if one_hour_ping == True:
            end_time = end_time - 3600
            await war.insert_one({
                "tag": new_war.clan.tag,
                "time" : end_time
            })

        if two_hour_ping == True:
            end_time = end_time - 7200
            await war.insert_one({
                "tag": new_war.clan.tag,
                "time": end_time
            })
        if four_hour_ping == True:
            end_time = end_time - 14400
            await war.insert_one({
                "tag": new_war.clan.tag,
                "time": end_time
            })
        if eight_hour_ping == True:
            end_time = end_time - 28800
            await war.insert_one({
                "tag": new_war.clan.tag,
                "time": end_time
            })


def setup(bot: commands.Bot):
    bot.add_cog(WarEvents(bot))