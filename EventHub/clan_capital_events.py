from disnake.ext import commands
import disnake

from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import player_ee
from main import scheduler

class clan_capital_events(commands.Cog, name="Clan Capital Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on("Most Valuable Clanmate", self.cg_dono_event)
        self.player_ee.on("Aggressive Capitalism", self.raid_event)
        scheduler.add_job(self.clan_capital_summary, "cron", day_of_week="mon", hour=7, minute=5)

    async def raid_event(self, event):
        dono_change = event["new_player"]["achievements"][-2]["value"] - event["old_player"]["achievements"][-2]["value"]
        try:
            clan_tag = event["new_player"]["clan"]["tag"]
        except:
            return
        # print(f"{new_player.name} donated {new_capital_dono.value - old_capital_dono.value}")
        tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue

            try:
                clancapital_channel = await server.fetch_channel(clancapital_channel)
                if clancapital_channel is None:
                    continue
            except:
                continue
            tag = event['new_player']['tag']
            embed = disnake.Embed(
                description=f"[**{event['new_player']['name']}**]({self.bot.create_link(tag=tag)}) raided <:capitalgold:987861320286216223>{dono_change}"
                , color=disnake.Color.orange())

            embed.set_footer(icon_url=event["new_player"]["clan"]["badgeUrls"]["large"], text=event["new_player"]["clan"]["name"])

            try:
                await clancapital_channel.send(embed=embed)
            except:
                continue

    async def cg_dono_event(self, event):
        #print(event["new_player"])
        #print(event["new_player"]["achievements"][-2]["value"])
        dono_change = event["new_player"]["achievements"][-1]["value"] - event["old_player"]["achievements"][-1][
            "value"]
        try:
            clan_tag = event["new_player"]["clan"]["tag"]
        except:
            return
        # print(f"{new_player.name} donated {new_capital_dono.value - old_capital_dono.value}")
        tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            clancapital_channel = cc.get("clan_capital")
            if clancapital_channel is None:
                continue

            try:
                clancapital_channel = await server.fetch_channel(clancapital_channel)
                if clancapital_channel is None:
                    continue
            except:
                continue

            tag = event['new_player']['tag']
            embed = disnake.Embed(
                description=f"[**{event['new_player']['name']}**]({self.bot.create_link(tag=tag)}) donated <:capitalgold:987861320286216223>{dono_change}"
                , color=disnake.Color.green())

            embed.set_footer(icon_url=event["new_player"]["clan"]["badgeUrls"]["large"],
                             text=event["new_player"]["clan"]["name"])

            try:
                await clancapital_channel.send(embed=embed)
            except:
                continue

    async def clan_capital_summary(self):
        pass
        #pseudo code
        #get last week's date
        #get all clan capital channels
        #send clan capital summary from last week to all channels with "zeros"


def setup(bot: CustomClient):
    bot.add_cog(clan_capital_events(bot))