from disnake.ext import commands
import coc
import asyncio
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from pymongo import UpdateOne

class lb_updater(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.leaderboard_cron, 'interval', minutes=60)


    async def leaderboard_cron(self):
        await self.bot.leaderboard_db.update_many({}, {"$set": {"global_rank": None, "local_rank": None}})
        lb_changes = []
        tasks = []
        for location in self.bot.locations:
            task = asyncio.ensure_future(self.bot.coc_client.get_location_players(location_id=location))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        for index, response in enumerate(responses):
            location = self.bot.locations[index]
            if location != "global":
                location = await self.bot.coc_client.get_location(location)
            for player in response:
                player: coc.RankedPlayer
                if location == "global":
                    lb_changes.append(
                        UpdateOne({"tag": player.tag}, {"$set": {f"global_rank": player.rank}}, upsert=True))
                else:
                    lb_changes.append(UpdateOne({"tag": player.tag},
                        {"$set": {f"local_rank": player.rank, f"country_name": location.name, f"country_code": location.country_code}}, upsert=True))

        if lb_changes != []:
            results = await self.bot.leaderboard_db.bulk_write(lb_changes)

        await self.bot.leaderboard_db.update_many({}, {"$set": {"builder_global_rank": None, "builder_local_rank": None}})
        lb_changes = []
        tasks = []
        for location in self.bot.locations:
            task = asyncio.ensure_future(self.bot.coc_client.get_location_players_versus(location_id=location))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        for index, response in enumerate(responses):
            location = self.bot.locations[index]
            if location != "global":
                location = await self.bot.coc_client.get_location(location)
            for player in response:
                player: coc.RankedPlayer
                if location == "global":
                    lb_changes.append(
                        UpdateOne({"tag": player.tag}, {"$set": {f"builder_global_rank": player.versus_rank}}, upsert=True))
                else:
                    lb_changes.append(UpdateOne({"tag": player.tag},
                                                {"$set": {f"builder_local_rank": player.versus_rank, f"country_name": location.name,
                                                          f"country_code": location.country_code}}, upsert=True))

        if lb_changes != []:
            results = await self.bot.leaderboard_db.bulk_write(lb_changes)

        #clan changes
        await self.bot.clan_leaderboard_db.update_many({}, {"$set": {"global_rank": None, "local_rank": None}})
        lb_changes = []
        tasks = []
        for location in self.bot.locations:
            task = asyncio.ensure_future(self.bot.coc_client.get_location_clans(location_id=location))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        for index, response in enumerate(responses):
            location = self.bot.locations[index]
            if location != "global":
                location = await self.bot.coc_client.get_location(location)
            for clan in response:
                clan: coc.RankedClan
                if location == "global":
                    lb_changes.append(
                        UpdateOne({"tag": clan.tag}, {"$set": {f"global_rank": clan.rank}}, upsert=True))
                else:
                    lb_changes.append(UpdateOne({"tag": clan.tag},
                                                {"$set": {f"local_rank": clan.rank, f"country_name": location.name,
                                                          f"country_code": location.country_code}}, upsert=True))

        if lb_changes != []:
            results = await self.bot.clan_leaderboard_db.bulk_write(lb_changes)

    async def update_clan_badges(self):

        tracked = self.bot.clan_db.find({})
        limit = await self.bot.clan_db.count_documents(filter={})
        for tClan in await tracked.to_list(length=limit):
            tag = tClan.get("tag")
            server = tClan.get("server")
            clan: coc.Clan = await self.bot.getClan(tag)
            if clan is None:
                continue
            try:
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": clan.tag},
                    {"server": server}
                ]}, {'$set': {"badge_link": clan.badge.url}})

            except:
                continue



def setup(bot: CustomClient):
    bot.add_cog(lb_updater(bot))