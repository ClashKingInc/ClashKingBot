import asyncio
from typing import TYPE_CHECKING

import coc
from disnake.ext import commands
from pymongo import UpdateOne

from classes.bot import CustomClient


class lb_updater(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.scheduler.add_job(self.leaderboard_cron, 'interval', minutes=60)

    async def update_clan_badges(self):

        tracked = self.bot.clan_db.find({})
        limit = await self.bot.clan_db.count_documents(filter={})
        for tClan in await tracked.to_list(length=limit):
            tag = tClan.get('tag')
            server = tClan.get('server')
            clan: coc.Clan = await self.bot.getClan(tag)
            if clan is None:
                continue
            try:
                await self.bot.clan_db.update_one(
                    {'$and': [{'tag': clan.tag}, {'server': server}]},
                    {'$set': {'badge_link': clan.badge.url}},
                )

            except:
                continue


def setup(bot: CustomClient):
    bot.add_cog(lb_updater(bot))
