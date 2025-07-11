from collections import namedtuple
from typing import Callable

import disnake
from exceptions.CustomExceptions import MissingWebhookPerms

from classes.bot import CustomClient
from classes.database.models.settings import ClanLog, DatabaseClan
from classes.events import CapitalEvent, ClanEvent, PlayerEvent
from utility.discord_utils import get_webhook_for_channel

MapItem = namedtuple('MapItem', ['database', 'cls'])
"""
database class should use this as well
"""


class LogMapping:
    join_log = MapItem(database='join_log', cls='join_log')


async def get_available_logs(
    bot: CustomClient, event: PlayerEvent | ClanEvent | CapitalEvent, log_type: LogMapping
) -> list[dict]:
    logs = []
    db = bot.clan_db
    """
    not 100% happy with this entire file, as it always feels like a weak spot 
    but it works, subclass if chain used so that the nested statements get type hinting
    first use of match statements, should be marginally faster than chained ifs at least
    formatting turned off to make this as easy to skim read as possible
    """
    # fmt: off
    if issubclass(event.__class__, ClanEvent):
        match log_type:
            case LogMapping.join_log.database:
                logs = await db.find(
                    {'$and': [{'tag': event.clan.tag}, {'logs.join_log.webhook': {'$ne': None}}]}
                ).to_list(length=None)

    elif issubclass(event.__class__, CapitalEvent):
        match event.event_type:

            case str(CapitalEvent.attack_log):
                logs = await db.find(
                    {'$and': [{'tag': event.clan.tag},{'logs.capital_attacks.webhook': {'$ne': None}}]}
                ).to_list(length=None)

    return logs
    # fmt: on


async def send_logs(
    bot: CustomClient,
    available_logs: list[dict],
    attribute: str,
    embeds: list[disnake.Embed],
    components: list[Callable],
):
    if not embeds:
        return

    for log in available_logs:
        db_clan = DatabaseClan(bot=bot, data=log)
        if db_clan.server_id not in bot.OUR_GUILDS:
            continue
        log: ClanLog = db_clan.__getattribute__(attribute)

        try:
            webhook = await bot.getch_webhook(log.webhook)
            if webhook.user.id != bot.user.id:
                webhook = await get_webhook_for_channel(bot=bot, channel=webhook.channel)
                await log.set_webhook(id=webhook.id)
            if log.thread is not None:
                thread = await bot.getch_channel(log.thread)
                if thread.locked:
                    continue
                for count, embed in enumerate(embeds):
                    await webhook.send(
                        embed=embed,
                        thread=thread,
                        components=components[count](log=log) if components else None,
                    )
            else:
                for count, embed in enumerate(embeds):
                    await webhook.send(
                        embed=embed,
                        components=components[count](log=log) if components else None,
                    )
        except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
            await log.set_thread(id=None)
            await log.set_webhook(id=None)
            continue
