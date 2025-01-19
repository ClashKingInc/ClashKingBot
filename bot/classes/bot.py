import asyncio
import calendar
import functools
import re
from datetime import datetime, timedelta
from math import ceil
from typing import Callable, Dict, List

import aiohttp
import coc
import dateutil.relativedelta
import disnake
import threading

import emoji
import motor.motor_asyncio
import pendulum as pend
import ujson
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from coc.ext import discordlinks
from disnake.ext import commands, fluent
from expiring_dict import ExpiringDict
from redis import asyncio as redis
import random

from classes.events import EventGateway
from classes.clashofstats import COSPlayerHistory
from classes.config import Config
from classes.database.familyclient import FamilyClient
from classes.emoji import Emojis, EmojiType
from classes.database.models.player.stats import CustomClanClass, StatsPlayer
from utility.constants import locations
from utility.general import create_superscript, fetch
from classes.cocpy.login import coc_login
from classes.mongo import MongoClient


class CustomClient(commands.AutoShardedBot):
    def __init__(
        self,
        config: Config,
        command_prefix: str,
        help_command,
        intents: disnake.Intents,
        scheduler: AsyncIOScheduler,
        shard_count: int | None,
        chunk_guilds_at_startup: bool,
        **kwargs,
    ):
        super().__init__(
            command_prefix=command_prefix,
            help_command=help_command,
            intents=intents,
            shard_count=shard_count,
            chunk_guilds_at_startup=chunk_guilds_at_startup,
            **kwargs,
        )
        self.VERSION = '1.0.6'

        self.i18n = fluent.FluentStore()
        self.i18n.load('locales/')

        self.event_gateway = EventGateway()

        self._config = config

        self.OUR_CLANS = set()

        self.SHARD_DATA: list[ShardData] = []
        self.SERVER_MAP: dict[int, ShardServers] = {}

        self.scheduler = scheduler
        self.ck_client: FamilyClient = None
        self.max_pool_size = 1 if config.is_custom else 100

        self.mongo = MongoClient()

        self.link_client: coc.ext.discordlinks.DiscordLinkClient = asyncio.get_event_loop().run_until_complete(
            discordlinks.login(self._config.link_api_username, self._config.link_api_password)
        )

        self.coc_client: coc.Client = asyncio.get_event_loop().run_until_complete(coc_login())

        self.loaded_emojis: dict = {}

        self.redis = redis.Redis(
            host=self._config.redis_ip,
            port=6379,
            db=0,
            password=self._config.redis_pw,
            retry_on_timeout=True,
            max_connections=250,
            retry_on_error=[redis.ConnectionError],
        )

        self.emoji: Emojis = None
        self.MAX_FEED_LEN = 5

        self.feed_webhooks = {}

        self.SETTINGS_CACHE = ExpiringDict()

        self.OUR_GUILDS = set()

        self.EXTENSION_LIST = []
        self.STARTED_CHUNK = set()

    def clean_string(self, text: str):
        text = emoji.replace_emoji(text)
        text = re.sub('[*_`~/]', '', text)
        return f'\u200e{text}'

    @staticmethod
    def get_guild_icon(guild: disnake.Guild | None):

        if guild is None:
            return None

        if guild.icon:
            return guild.icon.url

        return random.choice(placeholders)

    def get_locale(self, ctx: disnake.Interaction) -> disnake.Locale:

        if loc := ctx.locale:
            return loc

        return disnake.Locale.en_US

    def get_localizator(self, ctx: disnake.Interaction = None, locale: disnake.Locale = None):
        if not locale:
            locale = self.get_locale(ctx)

        def localizator_func(key, **kwargs):
            if 'values' in kwargs:
                return functools.partial(self.i18n.l10n, locale=locale, cache=False)(key, **kwargs)
            else:
                return functools.partial(self.i18n.l10n, locale=locale, cache=True)(key, **kwargs)

        return localizator_func, locale

    def get_server_localizator(self, server: disnake.Guild) -> Callable[[str], str]:
        return functools.partial(self.i18n.l10n, locale=server.preferred_locale or disnake.Locale.en_US)

    def get_number_emoji(self, color: str, number: int) -> EmojiType:
        emoji = self.fetch_emoji(f'{color}_{number}')
        return emoji

    async def get_webhook_for_channel(self, channel: disnake.TextChannel | disnake.Thread) -> disnake.Webhook:
        try:
            if isinstance(channel, disnake.Thread):
                webhooks = await channel.parent.webhooks()
            else:
                webhooks = await channel.webhooks()
            webhook = next((w for w in webhooks if w.user.id == self.user.id), None)
            if webhook is None:
                if isinstance(channel, disnake.Thread):
                    webhook = await channel.parent.create_webhook(
                        name=self.user.name, avatar=self.user.avatar, reason='Log Creation'
                    )
                else:
                    webhook = await channel.create_webhook(
                        name=self.user.name, avatar=self.user.avatar, reason='Log Creation'
                    )
            return webhook
        except Exception:
            raise MissingWebhookPerms

    async def get_family_member_tags(self, guild_id, th_filter: int = None):
        clan_tags = await self.clan_db.distinct('tag', filter={'server': guild_id})
        if th_filter is None:
            member_tags = await self.basic_clan.distinct('memberList.tag', filter={'tag': {'$in': clan_tags}})
        else:
            basic_clans = await self.basic_clan.find({'tag': {'$in': clan_tags}}, projection={'memberList': 1}).to_list(
                length=None
            )
            member_tags = [
                m.get('tag')
                for clan in basic_clans
                for m in clan.get('memberList', [])
                if m.get('townhall') == th_filter
            ]
        return member_tags

    async def get_clan_member_tags(self, clan_tags: list[str], legends_only=False):
        if not legends_only:
            member_tags = await self.basic_clan.distinct('memberList.tag', filter={'tag': {'$in': clan_tags}})
        else:
            basic_clans = await self.basic_clan.find({'tag': {'$in': clan_tags}}, projection={'memberList': 1}).to_list(
                length=None
            )
            member_tags = [
                m.get('tag')
                for clan in basic_clans
                for m in clan.get('memberList', [])
                if m.get('league') == 'Legend League'
            ]
        return member_tags

    async def get_mapped_clan_member_tags(self, clan_tags: List[str]) -> Dict[str, str]:
        basic_clans = await self.basic_clan.find(
            {'tag': {'$in': clan_tags}},
            projection={'tag': 1, 'memberList': 1, '_id': 0},
        ).to_list(length=None)
        mapped = {}
        for c in basic_clans:
            for m in c.get('memberList', []):
                mapped[m.get('tag')] = c.get('tag')
        return mapped

    async def get_guild_clans(self, guild_id):
        clan_tags = await self.clan_db.distinct('tag', filter={'server': guild_id})
        return clan_tags

    async def get_clan_name_mapping(self, clans: list[str]):
        basic_clans = await self.basic_clan.find(
            {'tag': {'$in': clans}}, projection={'tag': 1, '_id': 0, 'name': 1}
        ).to_list(length=None)
        names = {}
        mapping = {}
        for c in basic_clans:
            name = c.get('name')
            if names.get(name) is not None:
                num_found = names.get(name, 0)
                names[name] += 1
                name = name + create_superscript(num_found + 1)
            else:
                names[name] = 0
            mapping[c.get('tag')] = name
        return mapping

    # DISCORD HELPERS
    def partial_emoji_gen(self, emoji_string: str):
        emoji = emoji_string.split(':')
        animated = '<a:' in emoji_string
        return disnake.PartialEmoji(name=emoji[1], id=int(str(emoji[2])[:-1]), animated=animated)

    def fetch_emoji(self, name: str | int):
        if name == 'Unranked':
            name = 'unranked'
        emoji = self.loaded_emojis.get(name)
        if emoji is None:
            return None
        return EmojiType(emoji_string=emoji)

    async def getch_channel(self, channel_id, raise_exception=False):
        if (channel := self.get_channel(channel_id)) is not None:
            return channel

        try:
            return await self.fetch_channel(channel_id)
        except Exception:
            if raise_exception:
                raise
            return None

    async def getch_guild(self, guild_id, raise_exception=False):
        if (guild := self.get_guild(guild_id)) is not None:
            return guild

        try:
            return await self.fetch_guild(guild_id)
        except Exception:
            if raise_exception:
                raise
            return None

    async def getch_webhook(self, webhook_id):
        webhook = self.feed_webhooks.get(webhook_id)
        if webhook is None:
            webhook = await self.fetch_webhook(webhook_id)
            self.feed_webhooks[webhook_id] = webhook
        return webhook

    @staticmethod
    async def webhook_send(webhook: disnake.Webhook, **kwargs):
        thread = kwargs.pop('thread', None)
        if thread is None:
            msg = await webhook.send(**kwargs)
        else:
            msg = await webhook.send(thread=thread, **kwargs)
        return msg

    async def get_players(
        self,
        tags: list,
        fresh_tags=None,
        custom: bool | object = True,
        use_cache=True,
        fake_results=False,
        found_results=None,
        as_mapping=False,
    ):
        fresh_tags = fresh_tags or []

        tags = [p.split('|')[-1].strip() for p in tags]
        tags = [coc.utils.correct_tag(tag) for tag in tags]

        results_dict = {}
        results_list = found_results if found_results else []
        player_class = coc.Player
        if custom is not False and not fake_results:
            if custom is True:
                player_class = StatsPlayer
                results_list = await self.player_stats.find({'tag': {'$in': tags}}).to_list(length=None)
            else:
                player_class = custom
        elif custom is not False and fake_results:
            player_class = StatsPlayer
            results_dict = {tag: {} for tag in tags}
        results_dict.update({item.get('tag') or item.get('VillageTag'): item for item in results_list})

        players = []
        tag_set = set(tags)

        headers = {
            'Authorization': 'Bearer test',
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip',
        }
        data = [f"players/{t.replace('#', '%23')}" for t in tag_set]
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.clashk.ing/ck/bulk', json=data, headers=headers) as response:
                data = await response.read()
        player_data: dict = ujson.loads(data)
        players.extend(
            (player_class)(
                data=data,
                client=self.coc_client,
                bot=self,
                results=results_dict.get(data['tag'], {}),
            )
            for data in player_data
        )
        if as_mapping:
            return {p.tag: p for p in players}
        return players

    async def get_clans(self, tags: list, use_cache=True):
        tag_set = set(tags)

        if use_cache:
            cache_data = await self.clan_cache.find({'tag': {'$in': tags}}).to_list(length=2500)
        else:
            cache_data = []
        clans = []
        for data in cache_data:
            tag_set.remove(data.get('tag'))
            clans.append(CustomClanClass(data=data.get('data'), client=self.coc_client))

        tasks = []
        for tag in tag_set:
            task = asyncio.ensure_future(self.getClan(clan_tag=tag))
            tasks.append(task)
        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for response in responses:
                clans.append(response)
        return [clan for clan in clans if clan is not None]

    async def get_current_war_times(self, tags: list):
        tasks = []
        for tag in tags:
            task = asyncio.ensure_future(self.get_clanwar(clanTag=tag))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        times = {}
        for war in responses:  # type: coc.ClanWar
            if war is None:
                continue
            if war.end_time is None:
                continue
            times[war.clan.tag] = (war, war.end_time)
        return times

    async def get_clan_wars(self, tags: list):
        tasks = []
        for tag in tags:
            task = asyncio.ensure_future(self.get_clanwar(clanTag=tag))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        return responses

    async def store_all_cwls(self, clan: coc.Clan):
        await asyncio.sleep(0.1)
        from datetime import date

        diff = ceil((datetime.now().date() - date(2020, 12, 1)).days / 30)
        dates = self.gen_season_date(seasons_ago=diff, as_text=False)
        names = await self.cwl_db.distinct('season', filter={'clan_tag': clan.tag})
        await self.cwl_db.delete_many({'data.statusCode': 404})
        await self.cwl_db.delete_many({'data': None})
        missing = set(dates) - set(names)
        tasks = []
        async with aiohttp.ClientSession() as session:
            tag = clan.tag.replace('#', '')
            for date in missing:
                url = f'https://api.clashofstats.com/clans/{tag}/cwl/seasons/{date}'
                task = asyncio.ensure_future(fetch(url, session, extra=date))
                tasks.append(task)
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()

        for response, date in responses:
            try:
                if 'Not Found' not in str(response) and "'status': 500" not in str(response) and response is not None:
                    await self.cwl_db.insert_one({'clan_tag': clan.tag, 'season': date, 'data': response})
                else:
                    await self.cwl_db.insert_one({'clan_tag': clan.tag, 'season': date, 'data': None})
            except Exception:
                pass

    async def get_player_history(self, player_tag: str):
        url = f"https://api.clashofstats.com/players/{player_tag.replace('#', '')}/history/clans"
        async with aiohttp.ClientSession(headers={'User-Agent': self._config.clashofstats_user_agent}) as session:
            async with session.get(url) as resp:
                history = await resp.json()
                await session.close()
                return COSPlayerHistory(data=history)

    # SERVER HELPERS
    def get_command_mention(self, name: str):
        command = self.get_global_command_named(name=name.split(' ')[0])
        return f'</{name}:{command.id}>'

    async def white_list_check(self, ctx, command_name):
        if ctx.author.id == 706149153431879760:
            return True

        member = await ctx.guild.getch_member(member_id=ctx.author.id)
        if disnake.utils.get(member.roles, name='ClashKing Perms') is not None:
            return True

        guild = ctx.guild.id
        results = self.whitelist.find({'$and': [{'command': command_name}, {'server': guild}]})

        if results is None:
            return False

        perms = False
        for role in await results.to_list(length=None):
            role_ = role.get('role_user')
            is_role = role.get('is_role')
            if is_role:
                if disnake.utils.get(member.roles, id=int(role_)) is not None:
                    return True
            else:
                if member.id == role_:
                    return True

        return perms

    def command_names(self):
        commands = []
        for command_ in self.slash_commands:
            base_command = command_.name
            children = command_.children
            if children != {}:
                for child in children:
                    command = children[child]
                    full_name = f'{base_command} {command.name}'
                    commands.append(full_name)
            else:
                full_name = base_command
                commands.append(full_name)
        return commands


class ShardServers:
    def __init__(self, data: dict):
        self._data = data
        self.id: int = data.get('id')
        self.name: str = data.get('name')
        self.member_count: int = data.get('members')


class ShardData:
    def __init__(self, data: dict):
        self._data = data
        self.bot_id: int = data.get('bot_id')
        self.cluster_id: int = data.get('cluster_id')

        self.server_count: int = data.get('server_count')
        self.member_count: int = data.get('member_count')
        self.shards: list | None = data.get('shards')
        self.clan_count: int = data.get('clan_count')
        self.servers: list[ShardServers] = [ShardServers(data=s) for s in data.get('servers')]
