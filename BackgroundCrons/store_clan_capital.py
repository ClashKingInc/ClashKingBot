from disnake.ext import commands
import coc
import asyncio
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from utils.clash import weekend_timestamps
from pymongo import UpdateOne

class StoreClanCapital(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.store_cc, "cron", day_of_week="mon", hour=12)


    async def store_cc(self):
        tags = await self.bot.clan_db.distinct("tag")
        tasks = []
        date = self.bot.gen_raid_date()
        async def get_raidlog(tag):
            raidlog = await self.bot.coc_client.get_raidlog(tag)
            weekend_times = weekend_timestamps()
            raid_weekend = self.get_raid(raid_log=raidlog, before=weekend_times[1], after=weekend_times[2])
            return [raid_weekend, tag]

        for tag in tags:
            task = asyncio.ensure_future(get_raidlog(tag))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        updates = []
        for raid_weekend in responses:
            if raid_weekend[0] is None:
                continue
            for member in raid_weekend[0].members:
                if member is None:
                    continue
                updates.append(UpdateOne({"tag" : member.tag}, {"$set": {f"capital_gold.{date}.raided_clan": raid_weekend[1]}}, upsert=True))
                updates.append(UpdateOne({"tag": member.tag}, {"$set": {f"capital_gold.{date}.raid": [member.capital_resources_looted]}}, upsert=True))
                updates.append(UpdateOne({"tag": member.tag}, {"$set": {f"capital_gold.{date}.limit_hits": (member.attack_limit + member.bonus_attack_limit)}}, upsert=True))
                updates.append(UpdateOne({"tag": member.tag}, {"$set": {f"capital_gold.{date}.attack_count": member.attack_count}}, upsert=True))

        if updates != []:
            results = await self.bot.player_stats.bulk_write(updates)
            print(results.bulk_api_result)

    def get_raid(self, raid_log, after, before):
        for raid in raid_log:
            time_start = int(raid.start_time.time.timestamp())
            if before > time_start > after:
                return raid
        return None






def setup(bot: CustomClient):
    bot.add_cog(StoreClanCapital(bot))