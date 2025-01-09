import asyncio
import calendar
import functools
import io
import re
from datetime import datetime, timedelta
from math import ceil
from typing import Callable, Dict, List

import aiohttp
import coc
import dateutil.relativedelta
import disnake
import emoji
import motor.motor_asyncio
import pendulum as pend
import ujson
from aiocache import SimpleMemoryCache, cached
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from coc.ext import discordlinks
from disnake.ext import commands, fluent
from expiring_dict import ExpiringDict
from redis import asyncio as redis

from background.logs.events import kafka_events
from classes.clashofstats import COSPlayerHistory
from classes.config import Config
from classes.DatabaseClient.familyclient import FamilyClient
from classes.emoji import Emojis, EmojiType
from classes.player.stats import CustomClanClass, StatsPlayer
from utility.clash.other import is_cwl
from utility.constants import BADGE_GUILDS, locations
from utility.general import create_superscript, fetch
from utility.login import coc_login


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
        self.VERSION = '1.0.1'

        self.i18n = fluent.FluentStore()
        self.i18n.load('locales/')

        self.loop.create_task(kafka_events(self))

        self._config = config

        self.OUR_CLANS = set()

        self.SHARD_DATA: list[ShardData] = []
        self.SERVER_MAP: dict[int, ShardServers] = {}

        self.scheduler = scheduler
        self.ck_client: FamilyClient = None
        self.max_pool_size = 1 if config.is_custom else 100

        self.looper_db = motor.motor_asyncio.AsyncIOMotorClient(self._config.stats_mongodb, compressors='snappy' if config.is_main else 'zlib')

        self.new_looper = self.looper_db.get_database('new_looper')
        self.stats = self.looper_db.get_database(name='stats')
        self.cache = self.looper_db.get_database(name='cache')

        self.user_db = self.new_looper.get_collection('user_db')
        collection_class = self.user_db.__class__

        # NEW STATS
        self.base_player: collection_class = self.stats.base_player
        self.legends_stats: collection_class = self.stats.legends_stats
        self.season_stats: collection_class = self.stats.season_stats
        self.capital_cache: collection_class = self.cache.capital_raids

        self.player_stats: collection_class = self.new_looper.player_stats
        self.leaderboard_db: collection_class = self.new_looper.leaderboard_db
        self.clan_leaderboard_db: collection_class = self.new_looper.clan_leaderboard_db

        self.history_db: collection_class = self.looper_db.looper.legend_history
        self.warhits: collection_class = self.looper_db.looper.warhits
        self.webhook_message_db: collection_class = self.looper_db.looper.webhook_messages
        self.user_name = 'admin'
        self.cwl_db: collection_class = self.looper_db.looper.cwl_db
        self.leveling: collection_class = self.new_looper.leveling
        self.clan_wars: collection_class = self.looper_db.looper.clan_war
        self.command_stats: collection_class = self.new_looper.command_stats
        self.player_history: collection_class = self.new_looper.player_history
        self.clan_history: collection_class = self.new_looper.clan_history
        self.clan_cache: collection_class = self.new_looper.clan_cache
        self.excel_templates: collection_class = self.looper_db.clashking.excel_templates
        self.giveaways: collection_class = self.looper_db.clashking.giveaways
        self.tokens_db: collection_class = self.looper_db.clashking.tokens
        self.lineups: collection_class = self.looper_db.clashking.lineups
        self.bot_sync: collection_class = self.looper_db.clashking.bot_sync

        self.link_client: coc.ext.discordlinks.DiscordLinkClient = asyncio.get_event_loop().run_until_complete(
            discordlinks.login(self._config.link_api_username, self._config.link_api_password)
        )
        self.bot_stats: collection_class = self.looper_db.clashking.bot_stats
        self.clan_stats: collection_class = self.new_looper.clan_stats
        self.war_elo: collection_class = self.looper_db.looper.war_elo

        self.raid_weekend_db: collection_class = self.looper_db.looper.raid_weekends

        self.clan_join_leave: collection_class = self.looper_db.looper.join_leave_history

        self.base_stats: collection_class = self.looper_db.looper.base_stats
        self.clan_war: collection_class = self.looper_db.looper.clan_war
        self.cwl_groups: collection_class = self.looper_db.looper.cwl_group
        self.basic_clan: collection_class = self.looper_db.looper.clan_tags

        self.autoboards: collection_class = self.looper_db.clashking.autoboards

        self.legend_rankings: collection_class = self.new_looper.legend_rankings
        self.war_timers: collection_class = self.looper_db.looper.war_timer
        self.number_emojis: collection_class = self.looper_db.clashking.number_emojis

        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(
            self._config.static_mongodb, compressors='snappy' if config.is_main else 'zlib', maxPoolSize=self.max_pool_size
        )
        self.clan_db: collection_class = self.db_client.usafam.clans
        self.banlist: collection_class = self.db_client.usafam.banlist
        self.server_db: collection_class = self.db_client.usafam.server
        self.profile_db: collection_class = self.db_client.usafam.profile_db
        self.ignoredroles: collection_class = self.db_client.usafam.evalignore
        self.generalfamroles: collection_class = self.db_client.usafam.generalrole
        self.familyexclusiveroles: collection_class = self.db_client.usafam.familyexclusiveroles
        self.family_position_roles: collection_class = self.db_client.usafam.family_roles

        self.notfamroles: collection_class = self.db_client.usafam.linkrole
        self.townhallroles: collection_class = self.db_client.usafam.townhallroles
        self.builderhallroles: collection_class = self.db_client.usafam.builderhallroles
        self.legendleagueroles: collection_class = self.db_client.usafam.legendleagueroles
        self.builderleagueroles: collection_class = self.db_client.usafam.builderleagueroles
        self.donationroles: collection_class = self.db_client.usafam.donationroles
        self.achievementroles: collection_class = self.db_client.usafam.achievementroles
        self.statusroles: collection_class = self.db_client.usafam.statusroles
        self.welcome: collection_class = self.db_client.usafam.welcome
        self.erikuh: collection_class = self.db_client.usafam.erikuh
        self.button_db: collection_class = self.db_client.usafam.button_db
        self.legend_profile: collection_class = self.db_client.usafam.legend_profile
        self.youtube_channels: collection_class = self.db_client.usafam.youtube_channels
        self.reminders: collection_class = self.db_client.usafam.reminders
        self.whitelist: collection_class = self.db_client.usafam.whitelist
        self.rosters: collection_class = self.db_client.usafam.rosters
        self.credentials: collection_class = self.db_client.usafam.credentials
        self.global_chat_db: collection_class = self.db_client.usafam.global_chats
        self.global_reports: collection_class = self.db_client.usafam.reports
        self.strikelist: collection_class = self.db_client.usafam.strikes
        self.custom_bots: collection_class = self.db_client.usafam.custom_bots
        self.suggestions: collection_class = self.db_client.usafam.suggestions
        self.personal_reminders: collection_class = self.db_client.usafam.personal_reminders

        self.tickets: collection_class = self.db_client.usafam.tickets
        self.open_tickets: collection_class = self.db_client.usafam.open_tickets
        self.custom_embeds: collection_class = self.db_client.usafam.custom_embeds
        self.custom_commands: collection_class = self.db_client.usafam.custom_commands
        self.bases: collection_class = self.db_client.usafam.bases
        self.colors: collection_class = self.db_client.usafam.colors
        self.level_cards: collection_class = self.db_client.usafam.level_cards
        self.autostrikes: collection_class = self.db_client.usafam.autostrikes
        self.user_settings: collection_class = self.db_client.usafam.user_settings
        self.custom_boards: collection_class = self.db_client.usafam.custom_boards
        self.trials: collection_class = self.db_client.usafam.trials
        self.autoboard_db: collection_class = self.db_client.usafam.autoboard_db
        self.player_search: collection_class = self.db_client.usafam.player_search

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

        self.locations = locations

        self.emoji: Emojis = None
        self.MAX_FEED_LEN = 5
        self.FAQ_CHANNEL_ID = 1010727127806648371

        self.feed_webhooks = {}
        self.clan_list = []
        self.IMAGE_CACHE = ExpiringDict()

        self.SETTINGS_CACHE = ExpiringDict()

        self.OUR_GUILDS = set()

        self.EXTENSION_LIST = []
        self.STARTED_CHUNK = set()

        self.BADGE_GUILDS = BADGE_GUILDS

    def clean_string(self, text: str):
        text = emoji.replace_emoji(text)
        text = re.sub('[*_`~/]', '', text)
        return f'\u200e{text}'

    def timestamper(self, unix_time: int):
        class TimeStamp:
            def __init__(self, unix_time):
                self.slash_date = f'<t:{int(unix_time)}:d>'
                self.text_date = f'<t:{int(unix_time)}:D>'
                self.time_only = f'<t:{int(unix_time)}:t>'
                self.cal_date = f'<t:{int(unix_time)}:F>'
                self.relative = f'<t:{int(unix_time)}:R>'

        return TimeStamp(unix_time)

    async def create_new_badge_emoji(self, url: str):
        return self.emoji.blank.emoji_string

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

    async def track_clans(self, tags: list):
        result = await self.user_db.find_one({'username': self.user_name})
        tracked_list = result.get('tracked_clans')
        if tracked_list is None:
            tracked_list = []
        tracked_list = list(set(tracked_list + tags))
        await self.user_db.update_one({'username': self.user_name}, {'$set': {'tracked_clans': tracked_list}})
        return tracked_list

    async def get_tags(self, ping):
        ping = str(ping)
        if ping.startswith('<@') and ping.endswith('>'):
            ping = ping[2 : len(ping) - 1]

        if ping.startswith('!'):
            ping = ping[1 : len(ping)]
        id = ping
        try:
            tags = await self.link_client.get_linked_players(int(id))
        except Exception:
            tags = []
        return tags

    def gen_raid_date(self):
        now = datetime.utcnow().replace(tzinfo=pend.UTC)
        current_dayofweek = now.weekday()
        if (
            (current_dayofweek == 4 and now.hour >= 7)
            or (current_dayofweek == 5)
            or (current_dayofweek == 6)
            or (current_dayofweek == 0 and now.hour < 7)
        ):
            if current_dayofweek == 0:
                current_dayofweek = 7
            fallback = current_dayofweek - 4
            raidDate = (now - timedelta(fallback)).date()
            return str(raidDate)
        else:
            forward = 4 - current_dayofweek
            raidDate = (now + timedelta(forward)).date()
            return str(raidDate)

    def gen_season_date(self, seasons_ago=None, as_text=True):
        if seasons_ago is None:
            end = coc.utils.get_season_end().replace(tzinfo=pend.UTC).date()
            month = end.month
            if end.month <= 9:
                month = f'0{month}'
            return f'{end.year}-{month}'
        else:
            dates = []
            for x in range(0, seasons_ago + 1):
                end = coc.utils.get_season_end().replace(tzinfo=pend.UTC) - dateutil.relativedelta.relativedelta(months=x)
                if as_text:
                    dates.append(f'{calendar.month_name[end.date().month]} {end.date().year}')
                else:
                    month = end.month
                    if end.month <= 9:
                        month = f'0{month}'
                    dates.append(f'{end.year}-{month}')
            return dates

    def gen_games_season(self):
        now = datetime.utcnow()
        month = now.month
        if month <= 9:
            month = f'0{month}'
        return f'{now.year}-{month}'

    def gen_previous_season_date(self):
        end = coc.utils.get_season_start().replace(tzinfo=pend.UTC).date()
        month = end.month
        if end.month <= 9:
            month = f'0{month}'
        return f'{end.year}-{month}'

    def gen_legend_date(self):
        now = datetime.utcnow()
        hour = now.hour
        if hour < 5:
            date = (now - timedelta(1)).date()
        else:
            date = now.date()
        return str(date)

    async def get_reminder_times(self, clan_tag):
        all_reminders = self.reminders.find({'$and': [{'clan': clan_tag}, {'type': 'War'}]})
        limit = await self.reminders.count_documents(filter={'$and': [{'clan': clan_tag}, {'type': 'War'}]})
        times = set()
        for reminder in await all_reminders.to_list(length=limit):
            time = reminder.get('time')
            times.add(time)
        times = list(times)
        return times

    def get_times_in_range(self, reminder_times, war_end_time: coc.Timestamp):
        accepted_times = []
        for time in reminder_times:
            time = time.replace('hr', '')
            time = int(float(time) * 3600)
            if war_end_time.seconds_until >= time:
                reminder_time = war_end_time.time - timedelta(seconds=time)
                accepted_times.append([time, reminder_time])
        return accepted_times

    async def get_family_member_tags(self, guild_id, th_filter: int = None):
        clan_tags = await self.clan_db.distinct('tag', filter={'server': guild_id})
        if th_filter is None:
            member_tags = await self.basic_clan.distinct('memberList.tag', filter={'tag': {'$in': clan_tags}})
        else:
            basic_clans = await self.basic_clan.find({'tag': {'$in': clan_tags}}, projection={'memberList': 1}).to_list(length=None)
            member_tags = [m.get('tag') for clan in basic_clans for m in clan.get('memberList', []) if m.get('townhall') == th_filter]
        return member_tags

    async def get_clan_member_tags(self, clan_tags: list[str], legends_only=False):
        if not legends_only:
            member_tags = await self.basic_clan.distinct('memberList.tag', filter={'tag': {'$in': clan_tags}})
        else:
            basic_clans = await self.basic_clan.find({'tag': {'$in': clan_tags}}, projection={'memberList': 1}).to_list(length=None)
            member_tags = [m.get('tag') for clan in basic_clans for m in clan.get('memberList', []) if m.get('league') == 'Legend League']
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
        basic_clans = await self.basic_clan.find({'tag': {'$in': clans}}, projection={'tag': 1, '_id': 0, 'name': 1}).to_list(length=None)
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
        channel = self.get_channel(channel_id)
        if channel is not None:
            return channel
        try:
            channel = await self.fetch_channel(channel_id)
        except Exception:
            if raise_exception:
                raise
            return None
        return channel

    async def getch_guild(self, guild_id, raise_exception=False):
        guild = None
        try:
            guild = self.get_guild(guild_id)
            if guild is None:
                raise Exception
            return guild
        except Exception:
            pass
        try:
            guild = await self.fetch_guild(guild_id)
        except Exception as e:
            if raise_exception:
                raise e
        return guild

    async def getch_webhook(self, webhook_id):
        webhook = self.feed_webhooks.get(webhook_id)
        if webhook is None:
            webhook = await self.fetch_webhook(webhook_id)
            self.feed_webhooks[webhook_id] = webhook
        return webhook

    async def webhook_send(self, webhook: disnake.Webhook, **kwargs):
        thread = kwargs.pop('thread', None)
        if thread is None:
            msg = await webhook.send(**kwargs)
        else:
            msg = await webhook.send(thread=thread, **kwargs)
        return msg

    async def get_screenshot(self, player: coc.Player):
        tag = player.tag.replace('#', '')
        url = f'https://api.clashk.ing/ss/{tag}/706149153431879760'

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5 * 60)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()

        image_file = io.BytesIO(image_data)
        image_file.seek(0)

        return disnake.File(fp=image_file, filename='screenshot.png')

    # CLASH HELPERS
    async def getPlayer(self, player_tag, custom=False, raise_exceptions=False, cache_data=False):
        if '|' in player_tag:
            player_tag = player_tag.split('|')[-1]
        use_cache = cache_data
        player_tag = coc.utils.correct_tag(player_tag)
        if use_cache:
            cache_data = await self.redis.get(player_tag)
            if cache_data:
                cache_data = ujson.loads(cache_data)
        else:
            cache_data = None

        try:
            if custom is True:
                results = await self.player_stats.find_one({'tag': player_tag})
                if results is None:
                    results = {}
                if cache_data is None:
                    clashPlayer = await self.coc_client.get_player(
                        player_tag=player_tag,
                        cls=StatsPlayer,
                        bot=self,
                        results=results,
                    )
                else:
                    clashPlayer = StatsPlayer(
                        data=cache_data,
                        client=self.coc_client,
                        bot=self,
                        results=results,
                    )
            else:
                if cache_data is None:
                    clashPlayer: coc.Player = await self.coc_client.get_player(player_tag)
                    # await self.redis.set(clashPlayer.tag, ujson.dumps(clashPlayer._raw_data).encode('utf-8'), ex=120)
                else:
                    clashPlayer = coc.Player(data=cache_data, client=self.coc_client)
            return clashPlayer
        except Exception as e:
            if raise_exceptions:
                raise e
            else:
                return None

    async def get_players(
        self,
        tags: list,
        fresh_tags=None,
        custom: bool | object = True,
        use_cache=True,
        fake_results=False,
        found_results=None,
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

    async def getClan(self, clan_tag, raise_exceptions=False):
        if '|' in clan_tag:
            search = clan_tag.split('|')
            try:
                clan_tag = search[4]
            except:
                clan_tag = search[1]

        clan_tag = coc.utils.correct_tag(clan_tag)
        try:
            clan = await self.coc_client.get_clan(clan_tag, cls=CustomClanClass)
        except Exception:
            if raise_exceptions:
                raise
            return None
        if not raise_exceptions:
            if clan.member_count == 0:
                return None
        return clan

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

    async def get_clanwar(self, clanTag, next_war=False):
        if not next_war:
            try:
                war = await self.coc_client.get_current_war(clanTag)
                if war is None and is_cwl():
                    war = await self.coc_client.get_current_war(clanTag, cwl_round=coc.WarRound.current_preparation)
                if not war or war.state == 'notInWar':
                    return None
                return war
            except coc.PrivateWarLog:
                now = datetime.utcnow().timestamp()
                result = (
                    await self.clan_wars.find({'$and': [{'clans': clanTag}, {'custom_id': None}, {'endTime': {'$gte': now}}]})
                    .sort({'endTime': -1})
                    .to_list(length=None)
                )
                if not result:
                    return None
                result = result[0]
                clans: list = result.get('clans')
                clans.remove(clanTag)
                clan_to_use = clans[0]
                war = await self.coc_client.get_current_war(clan_tag=clan_to_use)
                raw_data = war._raw_data
                war = coc.ClanWar(client=self.coc_client, data=raw_data, clan_tag=war.opponent.tag)
                return war
        else:
            try:
                war = await self.coc_client.get_current_war(clanTag, cwl_round=coc.WarRound.current_preparation)
                if war.state == 'notInWar':
                    return None
                return war
            except:
                return None

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

    @cached(ttl=None, cache=SimpleMemoryCache)
    async def get_country_names(self):
        locations = await self.coc_client.search_locations()
        return locations

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
