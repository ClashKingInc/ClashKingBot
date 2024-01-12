import os
import re

import coc.errors
import motor.motor_asyncio
import uvicorn

from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.openapi.utils import get_openapi

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
import leagues, player, capital, other, clan, war, utility, ranking, redirect, game_data, bans, stats, list, server_info
from api_analytics.fastapi import Analytics
from fastapi.middleware.cors import CORSMiddleware

LOCAL = False
load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        if isinstance(e, coc.errors.NotFound) or isinstance(e, coc.errors.Maintenance) or isinstance(e, coc.errors.Forbidden):
            return JSONResponse({"reason" : e.reason, "message" : e.message}, status_code=e.status)


if not LOCAL:
    app.middleware("http")(catch_exceptions_middleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(Analytics, api_key="9f56d999-b945-4be5-8787-2448ab222ad3")



routers = [
    bans.router,
    player.router,
    clan.router,
    war.router,
    capital.router,
    leagues.router,
    ranking.router,
    stats.router,
    list.router,
    redirect.router,
    game_data.router,
    other.router,
    utility.router,
    server_info.router
]
for router in routers:
    app.include_router(router)


client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
other_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
redis = aioredis.Redis(host='85.10.200.219', port=6379, db=1, password=os.getenv("REDIS_PW"))

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

CACHED_SEASONS = []

def fix_tag(tag:str):
    tag = tag.replace('%23', '')
    tag = "#" + re.sub(r"[^A-Z0-9]+", "", tag.upper()).replace("O", "0")
    return tag

@app.on_event("startup")
async def startup_event():
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


@app.get("/", include_in_schema=False,
         response_class=RedirectResponse)
async def docs():
    return f"https://api.clashking.xyz/docs"



description = """
### Clash of Clans Based API 👑
- No Auth Required
- Ratelimit is largely 30 req/sec, 5 req/sec on post & large requests
- 300 second cache
- Not perfect, stats are collected by polling the Official API
- [Discord Server](https://discord.gg/gChZm3XCrS)

This content is not affiliated with, endorsed, sponsored, or specifically approved by Supercell and Supercell is not responsible for it. For more information see Supercell’s Fan Content Policy: www.supercell.com/fan-content-policy.
"""


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="ClashKingAPI",
        version="1.0",
        description=description,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == '__main__':
    if not LOCAL:
        uvicorn.run("main:app", host='0.0.0.0', port=443, ssl_keyfile="/etc/letsencrypt/live/api.clashking.xyz/privkey.pem",
                    ssl_certfile="/etc/letsencrypt/live/api.clashking.xyz/fullchain.pem", workers=6)
    else:
        uvicorn.run("main:app", host='localhost', port=80)

