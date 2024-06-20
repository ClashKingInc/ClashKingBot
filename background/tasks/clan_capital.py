import asyncio
from typing import TYPE_CHECKING

import coc
import disnake
from BoardCommands.Utils.Clan import clan_raid_weekend_donation_stats, clan_raid_weekend_raid_stats
from coc.raid import RaidLogEntry
from disnake.ext import commands
from ImageGen.ClanCapitalResult import generate_raid_result_image
from pymongo import UpdateOne

from classes.bot import CustomClient
from classes.server import DatabaseClan
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.clash.capital import gen_raid_weekend_datestrings, get_raidlog_entry
from utility.discord_utils import get_webhook_for_channel


class StoreClanCapital(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(
            self.store_cc,
            'cron',
            day_of_week='mon',
            hour=7,
            minute=45,
            misfire_grace_time=None,
        )
        self.bot.scheduler.add_job(
            self.send_boards,
            'cron',
            day_of_week='mon',
            hour=11,
            minute=30,
            misfire_grace_time=None,
        )

    async def send_boards(self):
        clan_tags = await self.bot.clan_db.distinct('tag', filter={'logs.capital_weekly_summary.webhook': {'$ne': None}})
        clans = await self.bot.get_clans(tags=clan_tags)
        for cc in await self.bot.clan_db.find({'logs.capital_weekly_summary.webhook': {'$ne': None}}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            log = db_clan.capital_weekly_summary

            clan = coc.utils.get(clans, tag=db_clan.tag)
            if clan is None:
                continue

            weekend = gen_raid_weekend_datestrings(2)[1]  # get previous weekend
            raid_log_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot, limit=1)
            if raid_log_entry is None:
                continue

            file = await generate_raid_result_image(raid_entry=raid_log_entry, clan=clan)
            raid_embed = await clan_raid_weekend_raid_stats(bot=self.bot, clan=clan, raid_log_entry=raid_log_entry)
            donation_embed = await clan_raid_weekend_donation_stats(clan=clan, weekend=weekend, bot=self.bot)
            donation_embed.set_image(file=file)

            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if isinstance(webhook.channel, disnake.ForumChannel) and log.thread is None:
                    raise MissingWebhookPerms
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread, raise_exception=True)
                    if thread.locked:
                        continue
                    await webhook.send(embed=raid_embed, thread=thread)
                    await webhook.send(embed=donation_embed, thread=thread)
                else:
                    await webhook.send(embed=raid_embed)
                    await webhook.send(embed=donation_embed)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

    async def store_cc(self):
        if not self.bot.user.public_flags.verified_bot:
            return
        tags = await self.bot.clan_db.distinct('tag')
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
            """if raid_log_entry is not None:
                await self.bot.raid_weekend_db.insert_one({
                    "clan_tag" : clan.tag,
                    "data" : raid_log_entry._raw_data
                })"""
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
                updates.append(
                    UpdateOne(
                        {'tag': member.tag},
                        {'$set': {f'capital_gold.{date}.raided_clan': clan.tag}},
                        upsert=True,
                    )
                )
                updates.append(
                    UpdateOne(
                        {'tag': member.tag},
                        {'$set': {f'capital_gold.{date}.raid': [member.capital_resources_looted]}},
                        upsert=True,
                    )
                )
                updates.append(
                    UpdateOne(
                        {'tag': member.tag},
                        {'$set': {f'capital_gold.{date}.limit_hits': (member.attack_limit + member.bonus_attack_limit)}},
                        upsert=True,
                    )
                )
                updates.append(
                    UpdateOne(
                        {'tag': member.tag},
                        {'$set': {f'capital_gold.{date}.attack_count': member.attack_count}},
                        upsert=True,
                    )
                )
                updates.append(
                    UpdateOne(
                        {'tag': member.tag},
                        {'$inc': {'points': member.capital_resources_looted * 0.25}},
                        upsert=True,
                    )
                )

        if updates != []:
            results = await self.bot.player_stats.bulk_write(updates)
            print(results.bulk_api_result)


def setup(bot: CustomClient):
    bot.add_cog(StoreClanCapital(bot))
