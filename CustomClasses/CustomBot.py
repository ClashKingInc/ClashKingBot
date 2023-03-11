import json
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
from urllib.request import urlopen
from collections import defaultdict
from utils.troop_methods import cwl_league_emojis
from CustomClasses.PlayerHistory import COSPlayerHistory

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

utc = pytz.utc
load_dotenv()
emoji_class = Emojis()
locations = ["global", 32000007, 32000008, 32000009, 32000010, 32000011, 32000012, 32000013, 32000014, 32000015, 32000016,
             32000017,
             32000018, 32000019, 32000020, 32000021, 32000022, 32000023, 32000024, 32000025, 32000026, 32000027,
             32000028,
             32000029, 32000030, 32000031, 32000032, 32000033, 32000034, 32000035, 32000036, 32000037, 32000038,
             32000039,
             32000040, 32000041, 32000042, 32000043, 32000044, 32000045, 32000046, 32000047, 32000048, 32000049,
             32000050,
             32000051, 32000052, 32000053, 32000054, 32000055, 32000056, 32000057, 32000058, 32000059, 32000060,
             32000061,
             32000062, 32000063, 32000064, 32000065, 32000066, 32000067, 32000068, 32000069, 32000070, 32000071,
             32000072,
             32000073, 32000074, 32000075, 32000076, 32000077, 32000078, 32000079, 32000080, 32000081, 32000082,
             32000083,
             32000084, 32000085, 32000086, 32000087, 32000088, 32000089, 32000090, 32000091, 32000092, 32000093,
             32000094,
             32000095, 32000096, 32000097, 32000098, 32000099, 32000100, 32000101, 32000102, 32000103, 32000104,
             32000105,
             32000106, 32000107, 32000108, 32000109, 32000110, 32000111, 32000112, 32000113, 32000114, 32000115,
             32000116,
             32000117, 32000118, 32000119, 32000120, 32000121, 32000122, 32000123, 32000124, 32000125, 32000126,
             32000127,
             32000128, 32000129, 32000130, 32000131, 32000132, 32000133, 32000134, 32000135, 32000136, 32000137,
             32000138,
             32000139, 32000140, 32000141, 32000142, 32000143, 32000144, 32000145, 32000146, 32000147, 32000148,
             32000149,
             32000150, 32000151, 32000152, 32000153, 32000154, 32000155, 32000156, 32000157, 32000158, 32000159,
             32000160,
             32000161, 32000162, 32000163, 32000164, 32000165, 32000166, 32000167, 32000168, 32000169, 32000170,
             32000171,
             32000172, 32000173, 32000174, 32000175, 32000176, 32000177, 32000178, 32000179, 32000180, 32000181,
             32000182,
             32000183, 32000184, 32000185, 32000186, 32000187, 32000188, 32000189, 32000190, 32000191, 32000192,
             32000193,
             32000194, 32000195, 32000196, 32000197, 32000198, 32000199, 32000200, 32000201, 32000202, 32000203,
             32000204,
             32000205, 32000206, 32000207, 32000208, 32000209, 32000210, 32000211, 32000212, 32000213, 32000214,
             32000215,
             32000216, 32000217, 32000218, 32000219, 32000220, 32000221, 32000222, 32000223, 32000224, 32000225,
             32000226,
             32000227, 32000228, 32000229, 32000230, 32000231, 32000232, 32000233, 32000234, 32000235, 32000236,
             32000237,
             32000238, 32000239, 32000240, 32000241, 32000242, 32000243, 32000244, 32000245, 32000246, 32000247,
             32000248,
             32000249, 32000250, 32000251, 32000252, 32000253, 32000254, 32000255, 32000256, 32000257, 32000258,
             32000259, 32000260]
BADGE_GUILDS = [1029631304817451078, 1029631182196977766, 1029631107240562689, 1029631144641183774, 1029629452403097651,
                             1029629694854828082, 1029629763087777862, 1029629811221610516, 1029629853017841754, 1029629905903833139,
                             1029629953907634286, 1029629992830783549, 1029630376911581255, 1029630455202455563, 1029630702125318144,
                             1029630796966932520, 1029630873588469760, 1029630918106824754, 1029630974025277470, 1029631012084396102]


class CustomClient(commands.AutoShardedBot):
    def __init__(self, **options):
        super().__init__(**options)
        self.looper_db = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
        self.new_looper = self.looper_db.new_looper
        self.user_db = self.new_looper.user_db
        self.player_stats = self.new_looper.player_stats
        self.leaderboard_db = self.new_looper.leaderboard_db
        self.clan_leaderboard_db = self.new_looper.clan_leaderboard_db
        self.history_db = self.looper_db.legend_history
        self.warhits = self.looper_db.looper.warhits
        self.webhook_message_db = self.looper_db.looper.webhook_messages
        self.user_name = "admin"
        self.cwl_db = self.looper_db.looper.cwl_db
        self.leveling = self.new_looper.leveling
        self.clan_wars = self.looper_db.looper.clan_wars
        self.player_cache = self.new_looper.player_cache

        self.link_client: coc.ext.discordlinks.DiscordLinkClient = asyncio.get_event_loop().run_until_complete(discordlinks.login(os.getenv("LINK_API_USER"), os.getenv("LINK_API_PW")))

        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
        self.clan_db = self.db_client.usafam.clans
        self.banlist = self.db_client.usafam.banlist
        self.server_db = self.db_client.usafam.server
        self.profile_db = self.db_client.usafam.profile_db
        self.ignoredroles = self.db_client.usafam.evalignore
        self.generalfamroles = self.db_client.usafam.generalrole
        self.notfamroles = self.db_client.usafam.linkrole
        self.townhallroles = self.db_client.usafam.townhallroles
        self.builderhallroles = self.db_client.usafam.builderhallroles
        self.legendleagueroles = self.db_client.usafam.legendleagueroles
        self.donationroles = self.db_client.usafam.donationroles
        self.welcome = self.db_client.usafam.welcome
        self.autoboards = self.db_client.usafam.autoboards
        self.erikuh = self.db_client.usafam.erikuh
        self.button_db = self.db_client.usafam.button_db
        self.legend_profile = self.db_client.usafam.legend_profile
        self.youtube_channels = self.db_client.usafam.youtube_channels
        self.reminders = self.db_client.usafam.reminders
        self.whitelist = self.db_client.usafam.whitelist
        self.rosters = self.db_client.usafam.rosters
        self.credentials = self.db_client.usafam.credentials
        self.global_chat_db = self.db_client.usafam.global_chats
        self.global_reports = self.db_client.usafam.reports
        self.strikelist = self.db_client.usafam.strikes
        self.raid_weekend_db = self.db_client.usafam.raid_weekends
        self.tickets = self.db_client.usafam.tickets
        self.open_tickets = self.db_client.usafam.open_tickets
        self.custom_embeds = self.db_client.usafam.custom_embeds
        self.custom_commands = self.db_client.usafam.custom_commands
        self.bases = self.db_client.usafam.bases
        self.colors = self.db_client.usafam.colors
        self.level_cards = self.db_client.usafam.level_cards
        self.autostrikes = self.db_client.usafam.autostrikes

        self.autoboard_db = self.db_client.usafam.autoboard_db

        self.coc_client = coc.EventsClient(key_count=10, key_names="DiscordBot", throttle_limit = 25,cache_max_size=50000, load_game_data=coc.LoadGameData(always=True), stats_max_size=10000)
        self.xyz = asyncio.get_event_loop().run_until_complete(self.coc_client.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD")))

        self.war_client: FullWarClient = asyncio.get_event_loop().run_until_complete(fullwarapi.login(username=os.getenv("FW_USER"), password=os.getenv("FW_PW"), coc_client=self.coc_client))

        self.emoji = emoji_class
        self.locations = locations

        self.MAX_FEED_LEN = 5
        self.FAQ_CHANNEL_ID = 1010727127806648371

        self.global_channels = []
        self.last_message = defaultdict(int)
        self.banned_global = [859653218979151892]
        self.global_webhooks = defaultdict(str)

        self.feed_webhooks = {}

        self.clan_list = []

    async def create_new_badge_emoji(self, url:str):
        new_url = url.replace(".png", "")
        all_emojis = self.emojis
        get_emoji = disnake.utils.get(all_emojis, name=new_url[-15:].replace("-", ""))
        if get_emoji is not None:
            return f"<:{get_emoji.name}:{get_emoji.id}>"

        img = urlopen(url).read()
        global BADGE_GUILDS
        guild_ids = collections.deque(BADGE_GUILDS)
        guild_ids.rotate(1)
        BADGE_GUILDS = list(guild_ids)

        guild = self.get_guild(BADGE_GUILDS[0])
        while len(guild.emojis) >= 47:
            num_to_delete = random.randint(1, 5)
            for emoji in guild.emojis[:num_to_delete]:
                await guild.delete_emoji(emoji=emoji)
            guild_ids = collections.deque(BADGE_GUILDS)
            guild_ids.rotate(1)
            BADGE_GUILDS = list(guild_ids)
            guild = self.get_guild(BADGE_GUILDS[0])

        emoji = await guild.create_custom_emoji(name=new_url[-15:].replace("-", ""), image=img)
        return f"<:{emoji.name}:{emoji.id}>"

    def get_number_emoji(self, color: str, number: int):
        guild = None
        if number <= 50:
            if color == "white":
                guild = self.get_guild(1042301258167484426)
            elif color == "blue":
                guild = self.get_guild(1042222078302109779)
            elif color == "gold":
                guild = self.get_guild(1042301195240357958)
        elif number >= 51:
            print(color)
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
        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('!')):
            ping = ping[1:len(ping)]
        id = ping
        tags = await self.link_client.get_linked_players(id)
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

    def gen_season_date(self, seasons_ago = None):
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
                dates.append(f"{calendar.month_name[end.date().month]} {end.date().year}")
            return dates

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


    def create_link(self, tag):
        tag = tag.replace("#", "%23")
        url = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag={tag}"
        return url

    #DISCORD HELPERS
    def partial_emoji_gen(self, emoji_string, animated=False):
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

    async def getch_channel(self, channel_id):
        try:
            channel = self.get_channel(channel_id)
            return channel
        except:
            pass
        channel = await self.fetch_channel(channel_id)
        return channel

    async def getch_webhook(self, channel_id):
        channel: disnake.TextChannel = await self.getch_channel(channel_id=channel_id)
        try:
            webhook = self.feed_webhooks[channel.id]
        except:
            webhooks = await channel.webhooks()
            if len(webhooks) == 0:
                bot_av = self.user.avatar.read().close()
                webhook = await channel.create_webhook(name=self.user.name, avatar=bot_av, reason="Feed Webhook")
            else:
                webhook = next(webhook for webhook in webhooks if webhook.user.id == self.user.id)
            self.feed_webhooks[channel.id] = webhook
        return webhook


    #CLASH HELPERS
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

    async def get_players(self, tags: list, custom=True, use_cache=True):
        import time
        t_ = time.time()
        if custom:
            results_list = await self.player_stats.find({"tag" : {"$in" : tags}}).to_list(length=2500)
            results_dict = {}
            for item in results_list:
                results_dict[item["tag"]] = item
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

    async def get_clans(self, tags: list):
        tasks = []
        for tag in tags:
            task = asyncio.ensure_future(self.getClan(clan_tag=tag))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)
        return [response for response in responses if response is not None]

    async def getClan(self, clan_tag, raise_exceptions=False):
        try:
            if "|" in clan_tag:
                search = clan_tag.split("|")
                try:
                    tag = search[4]
                except:
                    tag = search[1]
                clan = await self.coc_client.get_clan(tag)
                return clan
        except:
            pass
        if raise_exceptions:
            clan = await self.coc_client.get_clan(clan_tag)
        else:
            try:
                clan = await self.coc_client.get_clan(clan_tag)
            except:
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