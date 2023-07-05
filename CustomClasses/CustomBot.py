from datetime import datetime
from datetime import timedelta
from coc import utils
from coc.ext import discordlinks
from coc.ext.fullwarapi import FullWarClient
from coc.ext import fullwarapi
from disnake.ext import commands
from dotenv import load_dotenv
from Assets.emojiDictionary import emojiDictionary, legend_emojis
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.emoji_class import Emojis, EmojiType
from CustomClasses.CustomServer import DatabaseServer
from urllib.request import urlopen
from collections import defaultdict
from utils.clash import cwl_league_emojis
from CustomClasses.PlayerHistory import COSPlayerHistory
from utils.constants import locations, BADGE_GUILDS
from typing import Tuple, List
from utils import logins as login
from utils.general import fetch, get_clan_member_tags
from math import ceil
from expiring_dict import ExpiringDict

import dateutil.relativedelta
import ast
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
utc = pytz.utc
load_dotenv()

class CustomClient(commands.AutoShardedBot):
    def __init__(self, **options):
        super().__init__(**options)
        self.looper_db = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
        self.new_looper = self.looper_db.get_database("new_looper")
        self.user_db = self.new_looper.get_collection("user_db")
        collection_class = self.user_db.__class__

        self.player_stats: collection_class = self.new_looper.player_stats
        self.leaderboard_db: collection_class = self.new_looper.leaderboard_db
        self.clan_leaderboard_db: collection_class = self.new_looper.clan_leaderboard_db

        self.history_db = self.looper_db.looper.legend_history
        self.warhits: collection_class = self.looper_db.looper.warhits
        self.webhook_message_db: collection_class = self.looper_db.looper.webhook_messages
        self.user_name = "admin"
        self.cwl_db: collection_class = self.looper_db.looper.cwl_db
        self.leveling: collection_class = self.new_looper.leveling
        self.clan_wars: collection_class = self.looper_db.looper.clan_wars
        self.player_cache: collection_class = self.new_looper.player_cache
        self.command_stats: collection_class = self.new_looper.command_stats
        self.player_history: collection_class = self.new_looper.player_history
        self.clan_history: collection_class = self.new_looper.clan_history
        self.clan_cache: collection_class = self.new_looper.clan_cache
        self.excel_templates: collection_class = self.looper_db.clashking.excel_templates
        self.lineups: collection_class = self.looper_db.clashking.lineups
        self.link_client: coc.ext.discordlinks.DiscordLinkClient = asyncio.get_event_loop().run_until_complete(discordlinks.login(os.getenv("LINK_API_USER"), os.getenv("LINK_API_PW")))


        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
        self.clan_db: collection_class = self.db_client.usafam.clans
        self.banlist: collection_class = self.db_client.usafam.banlist
        self.server_db: collection_class = self.db_client.usafam.server
        self.profile_db: collection_class = self.db_client.usafam.profile_db
        self.ignoredroles: collection_class = self.db_client.usafam.evalignore
        self.generalfamroles: collection_class = self.db_client.usafam.generalrole
        self.notfamroles: collection_class = self.db_client.usafam.linkrole
        self.townhallroles: collection_class = self.db_client.usafam.townhallroles
        self.builderhallroles: collection_class = self.db_client.usafam.builderhallroles
        self.legendleagueroles: collection_class = self.db_client.usafam.legendleagueroles
        self.builderleagueroles: collection_class = self.db_client.usafam.builderleagueroles
        self.donationroles: collection_class = self.db_client.usafam.donationroles
        self.achievementroles: collection_class = self.db_client.usafam.achievementroles
        self.statusroles: collection_class = self.db_client.usafam.statusroles
        self.welcome: collection_class = self.db_client.usafam.welcome
        self.autoboards: collection_class = self.db_client.usafam.autoboards
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
        self.raid_weekend_db: collection_class = self.db_client.usafam.raid_weekends
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


        self.coc_client = login.coc_client

        self.war_client: FullWarClient = asyncio.get_event_loop().run_until_complete(fullwarapi.login(username=os.getenv("FW_USER"), password=os.getenv("FW_PW"), coc_client=self.coc_client))

        self.emoji = Emojis()
        self.locations = locations

        self.MAX_FEED_LEN = 5
        self.FAQ_CHANNEL_ID = 1010727127806648371

        self.global_channels = []
        self.last_message = defaultdict(int)
        self.banned_global = [859653218979151892]
        self.global_webhooks = defaultdict(str)

        self.feed_webhooks = {}
        self.clan_list = []
        self.player_cache_dict = {}
        self.IMAGE_CACHE = ExpiringDict()

        self.OUR_GUILDS = set()
        self.badge_guild = []

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
            have_created_guilds = disnake.utils.get(self.guilds, name="Badge Guild 1")
            if have_created_guilds is None:
                for x in range(1,6):
                    guild = await self.create_guild(name=f"Badge Guild {x}", icon=self.user.avatar)
                    self.badge_guild.append(guild.id)
            else:
                for x in range(1, 6):
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

    def get_number_emoji(self, color: str, number: int):
        if not self.user.public_flags.verified_bot:
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

    async def track_players(self, players: list):
        for player in players:
            r = await self.player_stats.find_one({"tag" : player.tag})
            if r is None:
                await self.player_stats.insert_one({"tag" : player.tag, "name" : player.name})
        return "Done"

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

    def create_embeds(self, line_lists, thumbnail_url=None, title=None, max_lines=25, color=disnake.Color.green(), footer=None):
        embed_texts = []
        lines = 0
        hold_text = ""
        for line in line_lists:
            hold_text += f"{line}\n"
            lines += 1
            if lines == max_lines:
                embed_texts.append(hold_text)
                hold_text = ""
                lines = 0

        if lines > 0:
            embed_texts.append(hold_text)

        embeds = []
        for text in embed_texts:
            embed = disnake.Embed(title=title,
                                  description=text
                                  , color=color)
            if thumbnail_url is not None:
                embed.set_thumbnail(url=thumbnail_url)
            if footer is not None:
                embed.set_footer(text=footer)
            embeds.append(embed)
        return embeds

    def parse_legend_search(self, smart_search):
        if "|" in smart_search and "#" in smart_search:
            search = smart_search.split("|")
            tag = search[-1]
        else:
            tag = smart_search
        return tag

    async def search_results(self, query):
        tags = []
        # if search is a player tag, pull stats of the player tag
        if utils.is_valid_tag(query) is True and len(query) >= 5:
            t = utils.correct_tag(tag=query)
            result = await self.player_stats.find_one({"tag": t})
            if result is not None:
                tags.append(t)
            return tags

        is_discord_id = query.isdigit()
        if is_discord_id:
            ttt = await self.get_tags(query)
            for tag in ttt:
                result = await self.player_stats.find_one({"$and": [
                    {"league": {"$eq": "Legend League"}},
                    {"tag": tag}
                ]})
                if result is not None:
                    tags.append(tag)
            if tags != []:
                return tags

        query = query.lower()
        query = re.escape(query)
        results = self.player_stats.find({
            "$and": [
                {"league": {"$eq": "Legend League"}},
                {
                    "name": {"$regex": f"^(?i).*{query}.*$"}
                }
            ]}
        ).limit(24)
        '''results = self.player_stats.find({"$and": [
            {"league": {"$eq": "Legend League"}},
            {"name": {"$regex": f"^(?i).*{query}.*$"}}
        ]})'''
        for document in await results.to_list(length=24):
            tags.append(document.get("tag"))
        return tags

    async def search_name_with_tag(self, query, poster=False):
        names = []
        if query != "" and poster is False:
            names.append(query)
        # if search is a player tag, pull stats of the player tag

        if len(query) >= 5 and utils.is_valid_tag(query) is True:
            t = utils.correct_tag(tag=query)
            query = query.lower()
            query = re.escape(query)
            results = self.player_stats.find({"$and": [
                {"league": {"$eq": "Legend League"}},
                {"tag": {"$regex": f"^(?i).*{t}.*$"}}
            ]}).limit(24)
            for document in await results.to_list(length=24):
                name = document.get("name")
                if name is None:
                    continue
                names.append(name + " | " + document.get("tag"))
            return names

        # ignore capitalization
        # results 3 or larger check for partial match
        # results 2 or shorter must be exact
        # await ongoing_stats.create_index([("name", "text")])

        query = query.lower()
        query = re.escape(query)
        results = self.player_stats.find({
            "$and": [
                {"league": {"$eq": "Legend League"}},
                {
                    "name": {"$regex": f"^(?i).*{query}.*$"}
                }
            ]}
        ).limit(24)
        for document in await results.to_list(length=24):
            names.append(document.get("name") + " | " + document.get("tag"))
        return names

    async def family_names(self, query, guild):
        names = []
        # if search is a player tag, pull stats of the player tag
        if query != "":
            names.append(query)
        clan_tags = await self.clan_db.distinct("tag", filter={"server": guild.id})
        if utils.is_valid_tag(query) is True:
            t = utils.correct_tag(tag=query)
            query = query.lower()
            query = re.escape(query)
            results = self.player_stats.find({"$and": [
                {"clan_tag": {"$in": clan_tags}},
                {"tag": {"$regex": f"^(?i).*{t}.*$"}}
            ]}).limit(24)
            for document in await results.to_list(length=25):
                name = document.get("name")
                if name is None:
                    continue
                names.append(name + " | " + document.get("tag"))
            return names[:25]

        # ignore capitalization
        # results 3 or larger check for partial match
        # results 2 or shorter must be exact
        # await ongoing_stats.create_index([("name", "text")])

        query = query.lower()
        query = re.escape(query)
        results = self.player_stats.find({"$and": [
            {"clan_tag": {"$in": clan_tags}},
            {"name": {"$regex": f"^(?i).*{query}.*$"}}
        ]}).limit(24)
        for document in await results.to_list(length=25):
            names.append(document.get("name") + " | " + document.get("tag"))
        return names[:25]

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

    def create_link(self, tag):
        tag = tag.replace("#", "%23")
        url = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={tag}"
        return url

    #DISCORD HELPERS
    def partial_emoji_gen(self, emoji_string, animated=False, state=None):
        emoji = emoji_string.split(":")
        #emoji = self.get_emoji(int(str(emoji[2])[:-1]))
        if "<a:" in emoji_string:
            animated = True
        emoji = disnake.PartialEmoji(name=emoji[1][1:], id=int(str(emoji[2])[:-1]), animated=animated)
        return emoji

    def fetch_emoji(self, name):
        emoji = emojiDictionary(name)
        if emoji is None:
            emoji = legend_emojis(name)
        if emoji is None:
            return None
        return EmojiType(emoji_string=emoji)

    async def pingToMember(self, ctx, ping, no_fetch=False):
        ping = str(ping)
        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('!')):
            ping = ping[1:len(ping)]
        if no_fetch:
            return ping
        try:
            guild: disnake.Guild = ctx.guild
            member = await guild.get_or_fetch_member(int(ping))
            return member
        except:
            return None

    async def pingToRole(self, ctx, ping):
        ping = str(ping)
        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('&')):
            ping = ping[1:len(ping)]

        try:
            roles = await ctx.guild.fetch_roles()
            role = utils.get(roles, id=int(ping))
            return role
        except:
            return None

    async def pingToChannel(self, ctx, ping):
        ping = str(ping)
        if (ping.startswith('<#') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        try:
            channel = ctx.guild.get_channel(int(ping))
            return channel
        except:
            return None

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
    async def store_all_cwls(self, clan: coc.Clan):
        await asyncio.sleep(0.1)
        from datetime import date
        diff = ceil((datetime.now().date() - date(2016, 12, 1)).days / 30)
        dates = self.gen_season_date(seasons_ago=diff, as_text=False)
        names = await self.cwl_db.distinct("season", filter={"clan_tag" : clan.tag})
        await self.cwl_db.delete_many({"data.statusCode" : 404})
        missing = set(dates) - set(names)
        tasks = []
        async with aiohttp.ClientSession() as session:
            tag = clan.tag.replace("#", "")
            for date in missing:
                url = f"https://api.clashofstats.com/clans/{tag}/cwl/seasons/{date}"
                task = asyncio.ensure_future(fetch(url, session, extra=date))
                tasks.append(task)
            responses = await asyncio.gather(*tasks)
            await session.close()

        for response, date in responses:
            try:
                if "Not Found" not in str(response) and "'status': 500" not in str(response) and response is not None:
                    await self.cwl_db.insert_one({"clan_tag": clan.tag, "season": date, "data": response})
                else:
                    await self.cwl_db.insert_one({"clan_tag": clan.tag, "season": date, "data": None})
            except:
                pass

    async def player_handle(self, ctx, tag):
        try:
            clashPlayer = await self.coc_client.get_player(tag)
        except:
            embed = disnake.Embed(description=f"{tag} is not a valid player tag.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

    async def getPlayer(self, player_tag, custom=False, raise_exceptions=False, cache_data=False):
        if "|" in player_tag:
            player_tag = player_tag.split("|")[-1]

        player_tag = coc.utils.correct_tag(player_tag)
        if cache_data:
            cache_data = await self.player_cache.find_one({"tag": player_tag})
        else:
            cache_data = None

        try:
            if custom is True:
                results = await self.player_stats.find_one({"tag": player_tag})
                if cache_data is None:
                    clashPlayer = await self.coc_client.get_player(player_tag=player_tag, cls=MyCustomPlayer, bot=self,
                                                                   results=results)
                else:
                    clashPlayer = MyCustomPlayer(data=cache_data.get("data"), client=self.coc_client, bot=self,
                                                 results=results)
            else:
                if cache_data is None:
                    clashPlayer: coc.Player = await self.coc_client.get_player(player_tag)
                else:
                    clashPlayer = coc.Player(data=cache_data.get("data"), client=self.coc_client)
            try:
                troops = clashPlayer.troops
            except:
                if custom is True:
                    results = await self.player_stats.find_one({"tag": player_tag})
                    clashPlayer = await self.coc_client.get_player(player_tag=player_tag, cls=MyCustomPlayer,bot=self,results=results)
                else:
                    clashPlayer: coc.Player = await self.coc_client.get_player(player_tag)
            return clashPlayer
        except Exception as e:
            if raise_exceptions:
                raise e
            else:
                return None

    async def get_players(self, tags: list, custom=True, use_cache=True, fake_results=False):
        if custom and fake_results is False:
            results_list = await self.player_stats.find({"tag" : {"$in" : tags}}).to_list(length=2500)
            results_dict = {}
            for item in results_list:
                results_dict[item["tag"]] = item
        elif custom and fake_results:
            results_dict = {tag: {} for tag in tags}

        players = []
        tag_set = set(tags)

        if use_cache:
            cache_data = await self.player_cache.find({"tag" : {"$in" : tags}}).to_list(length=2500)
        else:
            cache_data = []
        for data in cache_data:
            tag_set.remove(data.get("tag"))
            if not custom:
                player = coc.Player(data=data.get("data"), client=self.coc_client)
            else:
                player = MyCustomPlayer(data=data.get("data"), client=self.coc_client, bot=self, results=results_dict.get(data["tag"]))
            try:
                player.troops
                players.append(player)
            except:
                tag_set.add(data.get("tag"))
                continue
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
            clans.append(coc.Clan(data=data.get("data"), client=self.coc_client))

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
        clan_data = await self.clan_cache.find_one({"tag": clan_tag})
        try:
            if clan_data is None:
                clan = await self.coc_client.get_clan(clan_tag)
            else:
                clan = coc.Clan(data=clan_data.get("data"), client=self.coc_client)
        except:
            if raise_exceptions:
                raise
            return None
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

    async def verifyPlayer(self, playerTag:str, playerToken:str):
        verified = await self.coc_client.verify_player_token(playerTag, playerToken)
        return verified

    async def get_clanwar(self, clanTag, next_war = False):
        if not next_war:
            try:
                war = await self.coc_client.get_current_war(clanTag)
                return war
            except:
                return None
        else:
            try:
                war = await self.coc_client.get_current_war(clanTag, cwl_round=coc.WarRound.current_preparation)
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
    async def get_guild_members(self, guild_id):
        clan_tags = await self.clan_db.distinct("tag", filter={"server": guild_id})
        clans: List[coc.Clan] = await self.get_clans(tags=clan_tags)
        return get_clan_member_tags(clans=clans)

    async def get_guild_clans(self, guild_id):
        clan_tags = await self.clan_db.distinct("tag", filter={"server": guild_id})
        return clan_tags

    async def open_clan_capital_reminders(self):
        pass

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

    async def parse_to_embed(self, custom_json: str, clan: coc.Clan=None, guild: disnake.Guild = None):
        custom_json = custom_json.replace("true", "True")

        custom_json = custom_json.replace("`", '"')
        new_string = ""
        inside_string = False
        last_two = []
        for character in custom_json:
            if character == '"':
                inside_string = not inside_string

            if not inside_string and not character.isspace():
                new_string += character
            elif inside_string:
                new_string += character

        custom_json = new_string
        embed_json = re.findall('"embeds"(.*?)}]}\);', custom_json)
        embed_json = embed_json[0]

        embed_json = '{"embeds"' + embed_json + "}]}"
        if clan is not None:
            leader = coc.utils.get(clan.members, role=coc.Role.leader)
            leader_link = await self.link_client.get_link(leader.tag)
            if leader_link is None:
                leader_link = ""
            else:
                leader_link = f"<@{leader_link}>"
            clan_badge_emoji = await self.create_new_badge_emoji(url=clan.badge.url)
            possible_attributes = {"clan.name": clan.name, "clan.badge_url": clan.badge.url, "clan.tag": clan.tag, "clan.badge_emoji" : clan_badge_emoji,
                                   "clan.level": clan.level, "clan.type" : clan.type, "clan.war_frequency" : clan.war_frequency,
                                   "clan.member_count" : clan.member_count, "clan.war_league" : clan.war_league,
                                   "clan.war_league_emoji" : cwl_league_emojis(clan.war_league.name),
                                   "clan.required_townhall" : clan.required_townhall, "clan.required_townhall_emoji" : self.fetch_emoji(name=clan.required_townhall),
                                   "clan.leader" : leader.name , "clan.leader_discord" : leader_link,
                                   "clan.share_link": clan.share_link, "clan.description": clan.description,
                                   "clan.location": clan.location, "clan.points": clan.points,
                                   "clan.versus_points": clan.versus_points, "clan.capital_points": clan.capital_points,
                                   "clan.war_wins": clan.war_wins, "clan.member": clan.members}

            member_attributes = ["name", "trophies", "tag", "role", "exp_level", "league"]
            for attribute, replace in possible_attributes.items():
                if "{clan.member[" not in attribute:
                    embed_json = embed_json.replace(f"{{{attribute}}}", str(replace))
                elif "{clan.member[" in embed_json:
                    line_format = re.findall("{clan\.member\[(.*?)]}", embed_json)[0]
                    all_lines = ""
                    for member in clan.members:
                        this_line = line_format
                        for att in member_attributes:
                            if f"clan_member.{att}" in this_line:
                                this_line = this_line.replace(f"{{clan_member.{att}}}", str(getattr(member, att)))
                        all_lines += f"{this_line}" + r'\n'
                    embed_json = re.sub("{clan\.member(.*?)]}", all_lines, embed_json)

        if guild is not None:
            possible_attributes = {"guild.name": guild.name, "guild.icon" : guild.icon.url if guild.icon is not None else "",  "guild.banner" : guild.banner.url if guild.banner is not None else ""}
            for attribute, replace in possible_attributes.items():
                embed_json = embed_json.replace(f"{{{attribute}}}", str(replace))


        embed_json = ast.literal_eval(embed_json.replace('\r','\\r').replace('\n','\\n').replace("^^","`"))

        embed = disnake.Embed.from_dict(embed_json["embeds"][0])
        return embed

    async def split_family_buttons(self, button_text: str) -> Tuple[str, int, List[int], disnake.Guild]:
        split = str(button_text).split("_")
        season = split[1]
        limit = int(split[2])
        guild_id = split[3]
        townhall = split[4]
        if townhall != "None":
            townhall = [int(townhall)]
        else:
            townhall = list(range(2, 17))
        guild = await self.getch_guild(guild_id)
        if season == "None":
            season = self.gen_raid_date()
        return season, limit, townhall, guild

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

    def is_cwl(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        current_dayofweek = now.weekday()
        if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
                current_dayofweek == 0 and now.hour < 7):
            if current_dayofweek == 0:
                current_dayofweek = 7
            is_raids = True
        else:
            is_raids = False
        return is_raids


    #OTHER
    async def get_custom_clans(self, tags: List[str], server = disnake.Guild, add_clan=False):
        if add_clan:
            pass

        clan_db_results = await self.clan_db.find({"$and" : [{"tag" : {"$in" : tags}}, {"server" : server.id}]}).to_list(length=None)
        reminder_results = await self.clan_db.find({"$and" : [{"clan" : {"$in" : tags}}, {"server" : server.id}]})

    async def get_custom_server(self, guild_id):
        pipeline = [
            {"$match": {"server" : guild_id}},
            {"$lookup": {"from": "legendleagueroles", "localField": "server", "foreignField": "server", "as": "eval.league_roles"}},
            {"$lookup": {"from": "evalignore", "localField": "server", "foreignField": "server", "as": "eval.ignored_roles"}},
            {"$lookup": {"from": "generalrole", "localField": "server", "foreignField": "server", "as": "eval.family_roles"}},
            {"$lookup": {"from": "linkrole", "localField": "server", "foreignField": "server", "as": "eval.not_family_roles"}},
            {"$lookup": {"from": "townhallroles", "localField": "server", "foreignField": "server", "as": "eval.townhall_roles"}},
            {"$lookup": {"from": "builderhallroles", "localField": "server", "foreignField": "server", "as": "eval.builderhall_roles"}},
            {"$lookup": {"from": "achievementroles", "localField": "server", "foreignField": "server", "as": "eval.achievement_roles"}},
            {"$lookup": {"from": "statusroles", "localField": "server", "foreignField": "server", "as": "eval.status_roles"}},
            {"$lookup": {"from": "builderleagueroles", "localField": "server", "foreignField": "server", "as": "eval.builder_league_roles"}},
            {"$lookup": {"from": "clans", "localField": "server", "foreignField": "server", "as": "clans"}},
        ]
        results = await self.server_db.aggregate(pipeline).to_list(length=1)
        return DatabaseServer(bot=self, data=results[0])

    def get_clan_member_tags(self, clans):
        pass



