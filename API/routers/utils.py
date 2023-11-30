import motor.motor_asyncio
from redis import asyncio as aioredis
import redis
import os
import re
from dotenv import load_dotenv
import coc
import json
from pytz import utc
from datetime import datetime, timedelta
from coc.ext import discordlinks
import asyncio
from expiring_dict import ExpiringDict
import aiohttp
import io
IMAGE_CACHE = ExpiringDict()

load_dotenv()
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
other_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
redis = aioredis.Redis(host='85.10.200.219', port=6379, db=0, password=os.getenv("REDIS_PW"), retry_on_timeout=True, max_connections=25, retry_on_error=[redis.ConnectionError])

usafam = other_client.get_database("usafam")
clans_db = usafam.get_collection("clans")
collection_class = clans_db.__class__

player_search: collection_class = other_client.usafam.player_search

looper = client.looper
new_looper = client.new_looper

war_logs_db: collection_class = looper.war_logs
player_stats_db: collection_class = new_looper.player_stats
attack_db: collection_class = looper.warhits
player_leaderboard_db: collection_class = new_looper.leaderboard_db
player_history: collection_class = new_looper.get_collection("player_history")

clan_cache_db: collection_class = new_looper.clan_cache
clan_wars: collection_class = looper.clan_war
legend_history: collection_class = client.looper.legend_history
base_stats: collection_class = looper.base_stats
capital: collection_class = looper.raid_weekends
clan_stats: collection_class = new_looper.clan_stats
rankings: collection_class = new_looper.rankings
cwl_groups: collection_class = new_looper.cwl_group

clan_history: collection_class = new_looper.clan_history
clan_join_leave: collection_class = new_looper.clan_join_leave
ranking_history: collection_class = client.ranking_history
player_trophies: collection_class = ranking_history.player_trophies
player_versus_trophies: collection_class = ranking_history.player_versus_trophies
clan_trophies: collection_class = ranking_history.clan_trophies
clan_versus_trophies: collection_class = ranking_history.clan_versus_trophies
capital_trophies: collection_class = ranking_history.capital
basic_clan: collection_class = looper.clan_tags



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

leagues = ["Legend League", "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]