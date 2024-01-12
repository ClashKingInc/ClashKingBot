import ujson
import dateutil.relativedelta
import coc
import motor.motor_asyncio
import disnake
import pytz
import os
import re
import asyncio
import collections
import random
import calendar
import aiohttp
import emoji

from datetime import datetime, timedelta
from coc.ext import discordlinks
from disnake.ext import commands
from disnake import Message
from dotenv import load_dotenv
from Assets.emojiDictionary import emojiDictionary, legend_emojis
from CustomClasses.CustomPlayer import MyCustomPlayer, CustomClanClass
from CustomClasses.Emojis import Emojis, EmojiType
from urllib.request import urlopen
from collections import defaultdict
from CustomClasses.PlayerHistory import COSPlayerHistory
from Utils.constants import locations, BADGE_GUILDS
from typing import  List
from Utils.general import  get_clan_member_tags
from expiring_dict import ExpiringDict
from redis import asyncio as redis
from CustomClasses.DatabaseClient.familyclient import FamilyClient
utc = pytz.utc
load_dotenv()


class CustomClient(commands.AutoShardedBot):
    def __init__(self, **options):
        super().__init__(**options)

        self.ck_client: FamilyClient = None

        self.looper_db = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
        self.new_looper = self.looper_db.get_database("new_looper")
        self.user_db = self.new_looper.get_collection("user_db")
        collection_class = self.user_db.__class__

        self.player_stats: collection_class = self.new_looper.player_stats
        self.leaderboard_db: collection_class = self.new_looper.leaderboard_db
        self.clan_leaderboard_db: collection_class = self.new_looper.clan_leaderboard_db

        self.history_db: collection_class = self.looper_db.looper.legend_history
        self.warhits: collection_class = self.looper_db.looper.warhits
        self.webhook_message_db: collection_class = self.looper_db.looper.webhook_messages
        self.user_name = "admin"
        self.cwl_db: collection_class = self.looper_db.looper.cwl_db
        self.leveling: collection_class = self.new_looper.leveling
        self.clan_wars: collection_class = self.looper_db.looper.clan_war
        self.command_stats: collection_class = self.new_looper.command_stats
        self.player_history: collection_class = self.new_looper.player_history
        self.clan_history: collection_class = self.new_looper.clan_history
        self.clan_cache: collection_class = self.new_looper.clan_cache
        self.excel_templates: collection_class = self.looper_db.clashking.excel_templates
        self.lineups: collection_class = self.looper_db.clashking.lineups
        self.link_client: coc.ext.discordlinks.DiscordLinkClient = asyncio.get_event_loop().run_until_complete(discordlinks.login(os.getenv("LINK_API_USER"), os.getenv("LINK_API_PW")))
        self.bot_stats: collection_class = self.looper_db.clashking.bot_stats
        self.clan_stats: collection_class = self.new_looper.clan_stats
        self.raid_weekend_db: collection_class = self.looper_db.looper.raid_weekends
        self.clan_join_leave: collection_class = self.new_looper.clan_join_leave
        self.base_stats: collection_class = self.looper_db.looper.base_stats
        self.autoboards: collection_class = self.looper_db.clashking.autoboards
        self.clan_war: collection_class = self.looper_db.looper.clan_war
        self.cwl_groups: collection_class = self.new_looper.cwl_group
        self.basic_clan: collection_class = self.looper_db.looper.clan_tags
        self.button_store: collection_class = self.looper_db.clashking.button_store
        self.legend_rankings: collection_class = self.new_looper.legend_rankings

        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
        self.clan_db: collection_class = self.db_client.usafam.clans
        self.banlist: collection_class = self.db_client.usafam.banlist
        self.server_db: collection_class = self.db_client.usafam.server
        self.profile_db: collection_class = self.db_client.usafam.profile_db
        self.ignoredroles: collection_class = self.db_client.usafam.evalignore
        self.generalfamroles: collection_class = self.db_client.usafam.generalrole
        self.familyexclusiveroles: collection_class = self.db_client.usafam.familyexclusiveroles
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

        self.coc_client: coc.Client = coc.Client(loop=asyncio.get_event_loop_policy().get_event_loop(), key_count=10, key_names="DiscordBot", throttle_limit=500, cache_max_size=1000,
                                                load_game_data=coc.LoadGameData(always=False), raw_attribute=True, stats_max_size=10000)
        self._xyz = asyncio.get_event_loop().run_until_complete(self.coc_client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD")))

        self.redis = redis.Redis(host='85.10.200.219', port=6379, db=0, password=os.getenv("REDIS_PW"), retry_on_timeout=True, max_connections=25, retry_on_error=[redis.ConnectionError])

        self.emoji = Emojis()
        self.locations = locations

        self.MAX_FEED_LEN = 5
        self.FAQ_CHANNEL_ID = 1010727127806648371

        self.feed_webhooks = {}
        self.clan_list = []
        self.player_cache_dict = {}
        self.IMAGE_CACHE = ExpiringDict()

        self.OUR_GUILDS = set()
        self.badge_guild = []
        self.EXTENSION_LIST = []


    def clean_string(self, text: str):
        text = emoji.replace_emoji(text)
        text = re.sub('[*_`~/]', '', text)
        return f"\u200e{text}"

    def timestamper(self, unix_time: int):
        class TimeStamp():
            def __init__(self, unix_time):
                self.slash_date = f"<t:{int(unix_time)}:d>"
                self.text_date = f"<t:{int(unix_time)}:D>"
                self.time_only = f"<t:{int(unix_time)}:t>"
                self.cal_date = f"<t:{int(unix_time)}:F>"
                self.relative = f"<t:{int(unix_time)}:R>"
        return TimeStamp(unix_time)

    async def create_new_badge_emoji(self, url:str):
        if not self.user.public_flags.verified_bot and self.user.id != 808566437199216691 and self.badge_guild == []:
            guilds = await self.fetch_guilds().flatten()
            have_created_guilds = disnake.utils.get(guilds, name="Badge Guild 1")
            if have_created_guilds is None:
                for x in range(1,4):
                    guild = await self.create_guild(name=f"Badge Guild {x}", icon=self.user.avatar)
                    self.badge_guild.append(guild.id)
            else:
                for x in range(1, 4):
                    guild = disnake.utils.get(self.guilds, name=f"Badge Guild {x}")
                    self.badge_guild.append(guild.id)
        elif not self.badge_guild:
            self.badge_guild = BADGE_GUILDS

        new_url = url.replace(".png", "")
        all_emojis = self.emojis
        get_emoji = disnake.utils.get(all_emojis, name=new_url[-15:].replace("-", ""))
        if get_emoji is not None:
            return f"<:{get_emoji.name}:{get_emoji.id}>"

        img = urlopen(url).read()
        guild_ids = collections.deque(self.badge_guild)
        guild_ids.rotate(1)
        self.badge_guild = list(guild_ids)

        guild = self.get_guild(self.badge_guild[0])
        while len(guild.emojis) >= 47:
            num_to_delete = random.randint(1, 5)
            for emoji in guild.emojis[:num_to_delete]:
                await guild.delete_emoji(emoji=emoji)
            guild_ids = collections.deque(self.badge_guild)
            guild_ids.rotate(1)
            self.badge_guild = list(guild_ids)
            guild = self.get_guild(self.badge_guild[0])

        emoji = await guild.create_custom_emoji(name=new_url[-15:].replace("-", ""), image=img)
        return f"<:{emoji.name}:{emoji.id}>"

    def get_number_emoji(self, color: str, number: int) -> EmojiType:
        if not self.user.id == 808566437199216691 and not self.user.public_flags.verified_bot:
            color = "gold"
        guild = None
        if number <= 50:
            if color == "white":
                guild = self.get_guild(1042301258167484426)
            elif color == "blue":
                guild = self.get_guild(1042222078302109779)
            elif color == "gold":
                guild = self.get_guild(1042301195240357958)
        elif number >= 51:
            if color == "white":
                guild = self.get_guild(1042635651562086430)
            elif color == "blue":
                guild = self.get_guild(1042635521890992158)
            elif color == "gold":
                guild = self.get_guild(1042635608088125491)
        all_emojis = guild.emojis
        emoji = disnake.utils.get(all_emojis, name=f"{number}_")
        return EmojiType(emoji_string=f"<:{emoji.name}:{emoji.id}>")



    async def track_clans(self, tags: list):
        result = await self.user_db.find_one({"username": self.user_name})
        tracked_list = result.get("tracked_clans")
        if tracked_list is None:
            tracked_list = []
        tracked_list = list(set(tracked_list + tags))
        await self.user_db.update_one({"username": self.user_name}, {"$set": {"tracked_clans": tracked_list}})
        return tracked_list

    async def get_tags(self, ping):
        ping = str(ping)
        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('!')):
            ping = ping[1:len(ping)]
        id = ping
        try:
            tags = await self.link_client.get_linked_players(int(id))
        except Exception:
            tags = []
        return tags

    def gen_raid_date(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        current_dayofweek = now.weekday()
        if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
                current_dayofweek == 0 and now.hour < 7):
            if current_dayofweek == 0:
                current_dayofweek = 7
            fallback = current_dayofweek - 4
            raidDate = (now - timedelta(fallback)).date()
            return str(raidDate)
        else:
            forward = 4 - current_dayofweek
            raidDate = (now + timedelta(forward)).date()
            return str(raidDate)

    def gen_season_date(self, seasons_ago = None, as_text=True):
        if seasons_ago is None:
            end = coc.utils.get_season_end().replace(tzinfo=utc).date()
            month = end.month
            if end.month <= 9:
                month = f"0{month}"
            return f"{end.year}-{month}"
        else:
            dates = []
            for x in range(0, seasons_ago + 1):
                end = coc.utils.get_season_end().replace(tzinfo=utc) - dateutil.relativedelta.relativedelta(months=x)
                if as_text:
                    dates.append(f"{calendar.month_name[end.date().month]} {end.date().year}")
                else:
                    month = end.month
                    if end.month <= 9:
                        month = f"0{month}"
                    dates.append(f"{end.year}-{month}")
            return dates

    def gen_games_season(self):
        now = datetime.utcnow()
        month = now.month
        if month <= 9:
            month = f"0{month}"
        return f"{now.year}-{month}"

    def gen_previous_season_date(self):
        end = coc.utils.get_season_start().replace(tzinfo=utc).date()
        month = end.month
        if end.month <= 9:
            month = f"0{month}"
        return f"{end.year}-{month}"

    def gen_legend_date(self):
        now = datetime.utcnow()
        hour = now.hour
        if hour < 5:
            date = (now - timedelta(1)).date()
        else:
            date = now.date()
        return str(date)



    async def get_reminder_times(self, clan_tag):
        all_reminders = self.reminders.find({"$and": [
            {"clan": clan_tag},
            {"type": "War"}
        ]})
        limit = await self.reminders.count_documents(filter={"$and": [
            {"clan": clan_tag},
            {"type": "War"}
        ]})
        times = set()
        for reminder in await all_reminders.to_list(length=limit):
            time = reminder.get("time")
            times.add(time)
        times = list(times)
        return times

    def get_times_in_range(self, reminder_times, war_end_time: coc.Timestamp):
        accepted_times = []
        for time in reminder_times:
            time = time.replace("hr", "")
            time = int(float(time) * 3600)
            if war_end_time.seconds_until >= time:
                reminder_time = war_end_time.time - timedelta(seconds=time)
                accepted_times.append([time ,reminder_time])
        return accepted_times

    async def get_family_member_tags(self, guild_id):
        clan_tags = await self.clan_db.distinct("tag", filter={"server": guild_id})
        clans: List[coc.Clan] = await self.get_clans(tags=clan_tags)
        member_tags = get_clan_member_tags(clans=clans)
        return member_tags


    #DISCORD HELPERS
    def partial_emoji_gen(self, emoji_string: str):
        emoji = emoji_string.split(":")
        animated = "<a:" in emoji_string
        return disnake.PartialEmoji(name=emoji[1][1:], id=int(str(emoji[2])[:-1]), animated=animated)


    def fetch_emoji(self, name: str | int):
        emoji = emojiDictionary(name)
        if emoji is None:
            emoji = legend_emojis(name)
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


    async def webhook_send(self, webhook: disnake.Webhook, content="", embed=None, file=None, components=None, wait=False, thread=None):
        if thread is None:
            msg = await webhook.send(content=content, embed=embed, file=file, components=components, wait=wait)
        else:
            msg = await webhook.send(content=content, embed=embed, file=file, components=components, wait=wait, thread=thread)
        return msg


    #CLASH HELPERS
    async def getPlayer(self, player_tag, custom=False, raise_exceptions=False, cache_data=False):
        if "|" in player_tag:
            player_tag = player_tag.split("|")[-1]
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
                results = await self.player_stats.find_one({"tag": player_tag})
                if results is None:
                    results = {}
                if cache_data is None:
                    clashPlayer = await self.coc_client.get_player(player_tag=player_tag, cls=MyCustomPlayer, bot=self,
                                                                   results=results)
                else:
                    clashPlayer = MyCustomPlayer(data=cache_data, client=self.coc_client, bot=self, results=results)
            else:
                if cache_data is None:
                    clashPlayer: coc.Player = await self.coc_client.get_player(player_tag)
                    #await self.redis.set(clashPlayer.tag, ujson.dumps(clashPlayer._raw_data).encode('utf-8'), ex=120)
                else:
                    clashPlayer = coc.Player(data=cache_data, client=self.coc_client)
            return clashPlayer
        except Exception as e:
            if raise_exceptions:
                raise e
            else:
                return None

    async def get_players(self, tags: list, fresh_tags=None, custom=True, use_cache=True, fake_results=False, found_results=None):
        if fresh_tags is None:
            fresh_tags = []
        if custom and fake_results is False:
            if found_results is None:
                results_list = await self.player_stats.find({"tag" : {"$in" : tags}}).to_list(length=2500)
            else:
                results_list = found_results
            results_dict = {}
            for item in results_list:
                results_dict[item["tag"]] = item
        elif custom and fake_results:
            results_dict = {tag: {} for tag in tags}

        players = []
        tag_set = set(tags)
        if use_cache:
            cache_data = await self.redis.mget(keys=[tag for tag in tag_set if tag not in fresh_tags])
        else:
            cache_data = []

        for data in cache_data:
            if data is None:
                continue
            data = ujson.loads(data)
            tag_set.remove(data.get("tag"))
            if not custom:
                player = coc.Player(data=data, client=self.coc_client)
            else:
                player = MyCustomPlayer(data=data, client=self.coc_client, bot=self, results=results_dict.get(data["tag"]))
            players.append(player)

        tasks = []
        for tag in tag_set:
            task = asyncio.ensure_future(self.getPlayer(player_tag=tag, custom=custom))
            tasks.append(task)
        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for response in responses:
                players.append(response)
        return [player for player in players if player is not None]


    async def get_clans(self, tags: list, use_cache=True):
        tag_set = set(tags)

        if use_cache:
            cache_data = await self.clan_cache.find({"tag" : {"$in" : tags}}).to_list(length=2500)
        else:
            cache_data = []
        clans = []
        for data in cache_data:
            tag_set.remove(data.get("tag"))
            clans.append(CustomClanClass(data=data.get("data"), client=self.coc_client))

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
        if "|" in clan_tag:
            search = clan_tag.split("|")
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
        for war in responses: #type: coc.ClanWar
            if war is None:
                continue
            if war.end_time is None:
                continue
            times[war.clan.tag] = (war, war.end_time)
        return times


    async def get_clanwar(self, clanTag, next_war = False):
        if not next_war:
            try:
                war = await self.coc_client.get_current_war(clanTag)
                if war.state == "notInWar":
                    return None
                return war
            except coc.PrivateWarLog:
                now = datetime.utcnow().timestamp()
                result = await self.clan_war.find_one({"$and" : [{"endTime" : {"$gte" : now}}, {"opponent" : coc.utils.correct_tag(clanTag)}]})
                if result is None:
                    return None
                clan_to_use = result.get("clan")
                war = await self.coc_client.get_current_war(clan_tag=clan_to_use)
                raw_data = war._raw_data
                war = coc.ClanWar(client=self.coc_client, data=raw_data, clan_tag=war.opponent.tag)
                return war
        else:
            try:
                war = await self.coc_client.get_current_war(clanTag, cwl_round=coc.WarRound.current_preparation)
                if war.state == "notInWar":
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



    async def get_player_history(self, player_tag: str):
        url = f"https://api.clashofstats.com/players/{player_tag.replace('#', '')}/history/clans"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                history = await resp.json()
                await session.close()
                return COSPlayerHistory(data=history)


    #SERVER HELPERS

    async def get_guild_clans(self, guild_id):
        clan_tags = await self.clan_db.distinct("tag", filter={"server": guild_id})
        return clan_tags


    async def white_list_check(self, ctx, command_name):
        if ctx.author.id == 706149153431879760:
            return True
        member = ctx.author
        roles = (await ctx.guild.getch_member(member_id=ctx.author.id)).roles
        if disnake.utils.get(roles, name="ClashKing Perms") != None:
            return True

        commandd = command_name
        guild = ctx.guild.id
        results =  self.whitelist.find({"$and" : [
                {"command": commandd},
                {"server" : guild}
            ]})

        if results is None:
            return False

        limit = await self.whitelist.count_documents(filter={"$and" : [
                {"command": commandd},
                {"server" : guild}
            ]})

        perms = False
        for role in await results.to_list(length=limit):
            role_ = role.get("role_user")
            is_role = role.get("is_role")
            if is_role:
                role_ = ctx.guild.get_role(role_)
                if member in role_.members:
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
                    full_name = f"{base_command} {command.name}"
                    commands.append(full_name)
            else:
                full_name = base_command
                commands.append(full_name)
        return commands






