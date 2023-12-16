import motor.motor_asyncio
from redis import asyncio as aioredis
import redis
import os
import re
from dotenv import load_dotenv
import coc
from pytz import utc
from datetime import datetime, timedelta
from expiring_dict import ExpiringDict
import io
import asyncio
import aiohttp
from fastapi import HTTPException
import ujson
from base64 import b64decode as base64_b64decode
from json import loads as json_loads

IMAGE_CACHE = ExpiringDict()

load_dotenv()
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
other_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
redis = aioredis.Redis(host='85.10.200.219', port=6379, db=0, password=os.getenv("REDIS_PW"), retry_on_timeout=True, max_connections=25, retry_on_error=[redis.ConnectionError])
coc_client = coc.Client(key_count=100, key_names="DiscordBot", throttle_limit=500, cache_max_size=0, load_game_data=coc.LoadGameData(always=False), raw_attribute=True, stats_max_size=0)


class DBClient():
    def __init__(self):
        self.usafam = other_client.get_database("usafam")
        self.clans_db = self.usafam.get_collection("clans")
        self.server_db = self.usafam.server

        collection_class = self.clans_db.__class__

        self.server_db: collection_class = self.usafam.server
        self.clans_db: collection_class = self.usafam.get_collection("clans")
        self.banlist: collection_class = self.usafam.banlist

        self.player_search: collection_class = other_client.usafam.player_search

        self.looper = client.looper
        self.new_looper = client.new_looper

        self.war_logs_db: collection_class = self.looper.war_logs
        self.player_stats_db: collection_class = self.new_looper.player_stats
        self.attack_db: collection_class = self.looper.warhits
        self.player_leaderboard_db: collection_class = self.new_looper.leaderboard_db
        self.player_history: collection_class = self.new_looper.get_collection("player_history")

        self.clan_cache_db: collection_class = self.new_looper.clan_cache
        self.clan_wars: collection_class = self.looper.clan_war
        self.legend_history: collection_class = self.looper.legend_history
        self.base_stats: collection_class = self.looper.base_stats
        self.capital: collection_class = self.looper.raid_weekends
        self.clan_stats: collection_class = self.new_looper.clan_stats
        self.rankings: collection_class = self.new_looper.rankings
        self.cwl_groups: collection_class = self.new_looper.cwl_group

        self.clan_history: collection_class = self.new_looper.clan_history
        self.clan_join_leave: collection_class = self.new_looper.clan_join_leave
        self.ranking_history: collection_class = client.ranking_history
        self.player_trophies: collection_class = self.ranking_history.player_trophies
        self.player_versus_trophies: collection_class = self.ranking_history.player_versus_trophies
        self.clan_trophies: collection_class = self.ranking_history.clan_trophies
        self.clan_versus_trophies: collection_class = self.ranking_history.clan_versus_trophies
        self.capital_trophies: collection_class = self.ranking_history.capital
        self.basic_clan: collection_class = self.looper.clan_tags

db_client = DBClient()


async def get_players(tags: list, use_cache=True):
    players = []
    tag_set = set(tags)

    if use_cache:
        cache_data = await redis.mget(keys=list(tag_set))
    else:
        cache_data = []

    for data in cache_data:
        if data is None:
            continue
        data = ujson.loads(data)
        tag_set.remove(data.get("tag"))
        player = coc.Player(data=data, client=coc_client)
        players.append(player)

    await coc_client.get_player(list(tag_set)[0])
    tasks = []

    for tag in tag_set:
        task = asyncio.ensure_future(coc_client.get_player(tag))
        tasks.append(task)
    if tasks:
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for response in responses:
            if isinstance(response, coc.Player):
                players.append(response)
    return players


async def download_image(url: str):
    cached = IMAGE_CACHE.get(url)
    if cached is None:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                image_data = await response.read()
            await session.close()
        image_bytes: bytes = image_data
        IMAGE_CACHE.ttl(url, image_bytes, 3600 * 4)
    else:
        image_bytes = cached
    return io.BytesIO(image_bytes)

def fix_tag(tag:str):
    tag = tag.replace('%23', '')
    tag = "#" + re.sub(r"[^A-Z0-9]+", "", tag.upper()).replace("O", "0")
    return tag

def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=utc).date()
    month = end.month
    if end.month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"

def gen_games_season():
    now = datetime.utcnow()
    month = now.month
    if month <= 9:
        month = f"0{month}"
    return f"{now.year}-{month}"

def gen_raid_date():
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

async def token_verify(server_id: int, api_token: str):
    if api_token is None:
        raise HTTPException(status_code=403, detail="API Token is required")
    results = await db_client.server_db.find({"server" : {"$in" : [server_id, 1103679645439754335]}}).to_list(length=None)
    tokens = [r.get("api_token") for r in results]
    if api_token not in tokens:
        raise HTTPException(status_code=403, detail="Invalid API Token")

async def get_keys(emails: list, passwords: list, key_names: str, key_count: int):
    total_keys = []

    for count, email in enumerate(emails):
        _keys = []
        password = passwords[count]

        session = aiohttp.ClientSession()

        body = {"email": email, "password": password}
        resp = await session.post("https://developer.clashofclans.com/api/login", json=body)
        if resp.status == 403:
            raise RuntimeError(
                "Invalid Credentials"
            )

        resp_paylaod = await resp.json()
        ip = json_loads(base64_b64decode(resp_paylaod["temporaryAPIToken"].split(".")[1] + "====").decode("utf-8"))[
            "limits"][1]["cidrs"][0].split("/")[0]

        resp = await session.post("https://developer.clashofclans.com/api/apikey/list")
        keys = (await resp.json())["keys"]
        _keys.extend(key["key"] for key in keys if key["name"] == key_names and ip in key["cidrRanges"])

        for key in (k for k in keys if ip not in k["cidrRanges"]):
            await session.post("https://developer.clashofclans.com/api/apikey/revoke", json={"id": key["id"]})

        print(len(_keys))
        while len(_keys) < key_count:
            data = {
                "name": key_names,
                "description": "Created on {}".format(datetime.now().strftime("%c")),
                "cidrRanges": [ip],
                "scopes": ["clash"],
            }
            resp = await session.post("https://developer.clashofclans.com/api/apikey/create", json=data)
            key = await resp.json()
            _keys.append(key["key"]["key"])

        if len(keys) == 10 and len(_keys) < key_count:
            print("%s keys were requested to be used, but a maximum of %s could be "
                  "found/made on the developer site, as it has a maximum of 10 keys per account. "
                  "Please delete some keys or lower your `key_count` level."
                  "I will use %s keys for the life of this client.", )

        if len(_keys) == 0:
            raise RuntimeError(
                "There are {} API keys already created and none match a key_name of '{}'."
                "Please specify a key_name kwarg, or go to 'https://developer.clashofclans.com' to delete "
                "unused keys.".format(len(keys), key_names)
            )

        await session.close()
        for k in _keys:
            total_keys.append(k)

    print(len(total_keys))
    return (total_keys)


def create_keys(emails: list, passwords: list):
    done = False
    global API_KEYS
    while done is False:
        try:
            loop = asyncio.get_event_loop()
            keys = loop.run_until_complete(get_keys(emails=emails,
                                     passwords=passwords, key_names="test", key_count=10))
            done = True

            return keys
        except Exception as e:
            print(e)




leagues = ["Legend League", "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]