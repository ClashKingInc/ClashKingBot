import motor.motor_asyncio
from redis import asyncio as aioredis
import os
import re
from dotenv import load_dotenv
load_dotenv()
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
other_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
redis = aioredis.Redis(host='85.10.200.219', port=6379, db=0, password=os.getenv("REDIS_PW"))

player_search = other_client.usafam.player_search
looper = client.looper
new_looper = client.new_looper

war_logs_db = looper.war_logs
player_stats_db = new_looper.player_stats
attack_db = looper.warhits
player_leaderboard_db = new_looper.leaderboard_db
player_history = new_looper.get_collection("player_history")

player_cache_db = new_looper.player_cache
clan_cache_db = new_looper.clan_cache
clan_wars = looper.clan_war
legend_history = client.looper.legend_history
base_stats = looper.base_stats
capital = looper.raid_weekends
clan_stats = new_looper.clan_stats

clan_history = new_looper.clan_history
clan_join_leave = new_looper.clan_join_leave
ranking_history = client.ranking_history
player_trophies = ranking_history.player_trophies
player_versus_trophies = ranking_history.player_versus_trophies
clan_trophies = ranking_history.clan_trophies
clan_versus_trophies = ranking_history.clan_versus_trophies
capital_trophies = ranking_history.capital
basic_clan = looper.clan_tags

def fix_tag(tag:str):
    tag = tag.replace('%23', '')
    tag = "#" + re.sub(r"[^A-Z0-9]+", "", tag.upper()).replace("O", "0")
    return tag