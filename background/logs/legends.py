from typing import List, Optional

import disnake
import msgspec
import pendulum as pend
from disnake.ext import commands
from msgspec import Struct

from background.logs.events import player_ee
from classes.bot import CustomClient
from classes.server import DatabaseClan
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.discord_utils import get_webhook_for_channel


class Badges(Struct):
    large: str

    def to_dict(self):
        return {f: getattr(self, f) for f in self.__struct_fields__}


class Clan(Struct):
    name: str
    tag: str
    badgeUrls: Badges

    def to_dict(self):
        result = {f: getattr(self, f) for f in self.__struct_fields__}
        for field, value in result.items():
            if isinstance(value, Struct):
                result[field] = value.to_dict()  # Recursively convert nested structs
            elif isinstance(value, list) and all(isinstance(item, Struct) for item in value):
                result[field] = [item.to_dict() for item in value]  # Convert lists of structs

        return result


class Equipment(Struct):
    name: str
    level: int

    def to_dict(self):
        return {f: getattr(self, f) for f in self.__struct_fields__}


class Heroes(Struct):
    name: str
    equipment: Optional[List[Equipment]] = list()

    def to_dict(self):
        result = {f: getattr(self, f) for f in self.__struct_fields__}
        for field, value in result.items():
            if isinstance(value, Struct):
                result[field] = value.to_dict()  # Recursively convert nested structs
            elif isinstance(value, list) and all(isinstance(item, Struct) for item in value):
                result[field] = [item.to_dict() for item in value]  # Convert lists of structs

        return result


class League(Struct):
    name: str

    def to_dict(self):
        return {f: getattr(self, f) for f in self.__struct_fields__}


class Player(Struct):
    name: str
    tag: str
    trophies: int
    attackWins: int
    defenseWins: int
    heroes: List[Heroes]
    equipment: Optional[List[Equipment]] = list()
    clan: Optional[Clan] = None
    league: Optional[League] = None

    def to_dict(self):
        result = {f: getattr(self, f) for f in self.__struct_fields__}
        for field, value in result.items():
            if isinstance(value, Struct):
                result[field] = value.to_dict()  # Recursively convert nested structs
            elif isinstance(value, list) and all(isinstance(item, Struct) for item in value):
                result[field] = [item.to_dict() for item in value]  # Convert lists of structs

        return result

    def share_link(self):
        return f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23{self.tag.strip('#')}"


class LegendEvents(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.player_ee = player_ee
        self.player_ee.on('legends', self.legend_event)

    async def legend_event(self, event):
        player = msgspec.convert(event['new_data'], Player)
        if player.clan is None:
            return
        old_player = msgspec.convert(event['old_data'], Player)
        trophy_change = player.trophies - old_player.trophies

        utc_time = pend.now(tz=pend.UTC)

        if trophy_change >= 1:
            color = disnake.Color.green()
            change = f'{self.bot.emoji.sword} +{trophy_change} trophies'
            type = 'logs.legend_log_attacks.webhook'
        else:  # trophy_change <= -1
            color = disnake.Color.red()
            change = f'{self.bot.emoji.shield} {trophy_change} trophies'
            type = 'logs.legend_log_defenses.webhook'

        embed = disnake.Embed(description=f'{change} | [profile]({player.share_link()})', color=color)
        embed.set_author(
            name=f'{player.name} | {player.clan.name}',
            icon_url=player.clan.badgeUrls.large,
        )
        embed.set_footer(
            text=f'{player.trophies}',
            icon_url=self.bot.emoji.legends_shield.partial_emoji.url,
        )
        embed.timestamp = utc_time

        tracked = self.bot.clan_db.find({'$and': [{'tag': player.clan.tag}, {f'{type}': {'$ne': None}}]})
        for cc in await tracked.to_list(length=None):
            clan = DatabaseClan(bot=self.bot, data=cc)
            if clan.server_id not in self.bot.OUR_GUILDS:
                continue
            if trophy_change >= 1:
                log = clan.legend_log_attacks
            else:
                log = clan.legend_log_defenses
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if webhook.user.id != self.bot.user.id:
                    webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                    await log.set_webhook(id=webhook.id)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(embed=embed, thread=thread)
                else:
                    await webhook.send(embed=embed)
            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


def setup(bot: CustomClient):
    bot.add_cog(LegendEvents(bot))
