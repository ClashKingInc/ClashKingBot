from datetime import datetime
from datetime import timedelta
from coc import utils
from coc.ext import discordlinks
from disnake.ext import commands
from dotenv import load_dotenv
from Dictionaries.emojiDictionary import emojiDictionary, legend_emojis
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.emoji_class import Emojis

import coc
import motor.motor_asyncio
import disnake
import pytz
import os
import re

utc = pytz.utc
load_dotenv()
emoji_class = Emojis()

class CustomClient(commands.Bot):
    def __init__(self, **options):
        super().__init__(**options)

        self.looper_db = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
        self.new_looper = self.looper_db.new_looper
        self.user_db = self.new_looper.user_db
        self.player_stats = self.new_looper.player_stats
        self.user_name = "admin"

        self.link_client = discordlinks.login(os.getenv("LINK_API_USER"), os.getenv("LINK_API_PW"))

        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
        self.clan_db = self.db_client.usafam.clans
        self.banlist = self.db_client.usafam.banlist
        self.server_db = self.db_client.usafam.server
        self.profile_db = self.db_client.usafam.profile_db

        self.coc_client = coc.login(os.getenv("COC_EMAIL"), os.getenv("COC_PASSWORD"), client=coc.EventsClient, key_count=10, key_names="DiscordBot", throttle_limit = 30, cache_max_size=50000)

        #EMOJIS
        self.emoji = emoji_class

    async def track_players(self, tags: list):
        result = await self.user_db.find_one({"username": self.user_name})
        tracked_list = result.get("tracked_players")
        if tracked_list is None:
            tracked_list = []
        tracked_list = list(set(tracked_list + tags))
        await self.user_db.update_one({"username": self.user_name}, {"$set": {"tracked_players": tracked_list}})
        return tracked_list

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

    def gen_season_date(self):
        start = utils.get_season_start().replace(tzinfo=utc).date()
        year_add = 0
        if start == 12:
            start = 0
            year_add += 1
        month = start.month + 1
        if month <= 9:
            month = f"0{month}"
        year = start.year + year_add
        return f"{year}-{month}"

    def gen_legend_date(self):
        now = datetime.utcnow()
        hour = now.hour
        if hour < 5:
            date = (now - timedelta(1)).date()
        else:
            date = now.date()
        return str(date)

    def create_embeds(self, line_lists, thumbnail_url=None, title=None, max_lines=25, color=disnake.Color.green()):
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
            tags.append(t)
            return tags

        is_discord_id = query.isdigit()
        if is_discord_id:
            ttt = await self.get_tags(query)
            for tag in ttt:
                result = await self.player_stats.find_one({"$and": [
                    {"tag": tag},
                    {"league": {"$eq": "Legend League"}}
                ]})
                if result is not None:
                    tags.append(tag)
            if tags != []:
                return tags

        query = query.lower()
        query = re.escape(query)
        results = self.player_stats.find({"$and": [
            {"name": {"$regex": f"^(?i).*{query}.*$"}},
            {"league": {"$eq": "Legend League"}}
        ]})
        for document in await results.to_list(length=24):
            tags.append(document.get("tag"))
        return tags

    async def search_name_with_tag(self, query, poster=False):
        names = []
        if query != "" and poster is False:
            names.append(query)
        # if search is a player tag, pull stats of the player tag

        if utils.is_valid_tag(query) is True:
            t = utils.correct_tag(tag=query)
            query = query.lower()
            query = re.escape(query)
            results = self.player_stats.find({"$and": [
                {"tag": {"$regex": f"^(?i).*{t}.*$"}}
                , {"league": {"$eq": "Legend League"}}
            ]})
            for document in await results.to_list(length=24):
                names.append(document.get("name") + " | " + document.get("tag"))
            return names

        # ignore capitalization
        # results 3 or larger check for partial match
        # results 2 or shorter must be exact
        # await ongoing_stats.create_index([("name", "text")])

        query = query.lower()
        query = re.escape(query)
        results = self.player_stats.find({"$and": [
            {"name": {"$regex": f"^(?i).*{query}.*$"}}
            , {"league": {"$eq": "Legend League"}}
        ]})
        for document in await results.to_list(length=24):
            names.append(document.get("name") + " | " + document.get("tag"))
        return names


    #DISCORD HELPERS
    def partial_emoji_gen(self, emoji_string, animated=False):
        emoji = emoji_string.split(":")
        #emoji = self.get_emoji(int(str(emoji[2])[:-1]))
        emoji = disnake.PartialEmoji(name=emoji[1][1:], id=int(str(emoji[2])[:-1]), animated=animated)
        return emoji

    def fetch_emoji(self, name):
        emoji = emojiDictionary(name)
        if emoji is None:
            emoji = legend_emojis(name)
        return emoji

    async def pingToMember(self, ctx, ping):
        ping = str(ping)
        if (ping.startswith('<@') and ping.endswith('>')):
            ping = ping[2:len(ping) - 1]

        if (ping.startswith('!')):
            ping = ping[1:len(ping)]

        try:
            member = await ctx.guild.fetch_member(ping)
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


    #CLASH HELPERS
    async def player_handle(self, ctx, tag):
        try:
            clashPlayer = await self.coc_client.get_player(tag)
        except:
            embed = disnake.Embed(description=f"{tag} is not a valid player tag.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

    async def getPlayer(self, player_tag, custom=False):
        try:
            if custom is True:
                results = await self.player_stats.find_one({"tag": player_tag})
                clashPlayer = await self.coc_client.get_player(player_tag=player_tag, cls=MyCustomPlayer, bot=self,
                                                          results=results)
            else:
                clashPlayer: coc.Player = await self.coc_client.get_player(player_tag)
            return clashPlayer
        except:
            return None

    async def getClan(self, clan_tag):
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

        try:
            clan = await self.coc_client.get_clan(clan_tag)
            return clan
        except:
            return None

    async def verifyPlayer(self, playerTag, playerToken):
        verified = await self.coc_client.verify_player_token(playerTag, playerToken)
        return verified

    async def getClanWar(self, clanTag):
        try:
            war = await self.coc_client.get_clan_war(clanTag)
            return war
        except:
            return None



