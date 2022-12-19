from disnake.ext import commands
import coc
import asyncio
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from utils.ClanCapital import get_raidlog_entry, gen_raid_weekend_datestrings
from pymongo import UpdateOne
from coc.raid import RaidLogEntry

class StoreClanCapital(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.store_cc, "cron", day_of_week="mon", hour=7, minute=30)

    async def store_cc(self):
        tags = await self.bot.clan_db.distinct("tag")
        tasks = []
        date = self.bot.gen_raid_date()

        weekend = gen_raid_weekend_datestrings(2)[1]
        clans: list[coc.Clan] = await self.bot.get_clans(tags=tags)
        clans = [clan for clan in clans if clan is not None]

        async def get_raid(tag):
            clan = coc.utils.get(clans, tag=tag)
            if clan is None:
                return (None, None)
            raid_log_entry: RaidLogEntry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot)
            if raid_log_entry is not None:
                await self.bot.raid_weekend_db.insert_one({
                    "clan_tag" : clan.tag,
                    "data" : raid_log_entry._raw_data
                })
            return (clan, raid_log_entry)

        for tag in tags:
            task = asyncio.ensure_future(get_raid(tag))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        updates = []
        for clan, raid_log_entry in responses:
            if raid_log_entry is None:
                continue
            raid_log_entry: RaidLogEntry
            for member in raid_log_entry.members:
                if member is None:
                    continue
                updates.append(UpdateOne({"tag" : member.tag}, {"$set": {f"capital_gold.{date}.raided_clan": clan.tag}}, upsert=True))
                updates.append(UpdateOne({"tag": member.tag}, {"$set": {f"capital_gold.{date}.raid": [member.capital_resources_looted]}}, upsert=True))
                updates.append(UpdateOne({"tag": member.tag}, {"$set": {f"capital_gold.{date}.limit_hits": (member.attack_limit + member.bonus_attack_limit)}}, upsert=True))
                updates.append(UpdateOne({"tag": member.tag}, {"$set": {f"capital_gold.{date}.attack_count": member.attack_count}}, upsert=True))

        if updates != []:
            results = await self.bot.player_stats.bulk_write(updates)
            print(results.bulk_api_result)






def setup(bot: CustomClient):
    bot.add_cog(StoreClanCapital(bot))