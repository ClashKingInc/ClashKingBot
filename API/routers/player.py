import re
import ujson
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import player_stats_db, player_leaderboard_db, player_history, attack_db, fix_tag, legend_history, player_cache_db, player_search, redis

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Player Endpoints"])


@router.get("/player/{player_tag}/stats",
         tags=["Player Endpoints"],
         name="All collected Stats for a player (clan games, looted, activity, etc)")
@cache(expire=300)
@limiter.limit("30/second")
async def player_stat(player_tag: str, request: Request, response: Response):
    player_tag = player_tag and "#" + re.sub(r"[^A-Z0-9]+", "", player_tag.upper()).replace("O", "0")
    result = await player_stats_db.find_one({"tag": player_tag})
    lb_spot = await player_leaderboard_db.find_one({"tag": player_tag})

    if result is None:
        raise HTTPException(status_code=404, detail=f"No player found")
    try:
        del result["legends"]["streak"]
    except:
        pass
    result = {
        "name" : result.get("name"),
        "tag" : result.get("tag"),
        "townhall" : result.get("townhall"),
        "legends" : result.get("legends"),
        "last_online" : result.get("last_online"),
        "looted" : {"gold": result.get("gold", {}), "elixir": result.get("elixir", {}), "dark_elixir": result.get("dark_elixir", {})},
        "trophies" : result.get("trophies", 0),
        "warStars" : result.get("warStars"),
        "clanCapitalContributions" : result.get("aggressive_capitalism"),
        "donations": result.get("donations"),
        "capital" : result.get("capital_gold"),
        "clan_games" : result.get("clan_games"),
        "season_pass" : result.get("season_pass"),
        "activity" : result.get("activity"),
        "clan_tag" : result.get("clan_tag"),
        "league" : result.get("league")
    }

    if lb_spot is not None:
        try:
            result["legends"]["global_rank"] = lb_spot["global_rank"]
            result["legends"]["local_rank"] = lb_spot["local_rank"]
        except:
            pass
        try:
            result["location"] = lb_spot["country_name"]
        except:
            pass

    return result


@router.get("/player/{player_tag}/legends",
         tags=["Player Endpoints"],
         name="Legend stats for a player")
@cache(expire=300)
@limiter.limit("30/second")
async def player_legend(player_tag: str, request: Request, response: Response):
    player_tag = player_tag and "#" + re.sub(r"[^A-Z0-9]+", "", player_tag.upper()).replace("O", "0")
    result = await player_stats_db.find_one({"tag": player_tag})
    lb_spot = await player_leaderboard_db.find_one({"tag": player_tag})

    if result is None:
        raise HTTPException(status_code=404, detail=f"No player found")

    result = {
        "name" : result.get("name"),
        "townhall" : result.get("townhall"),
        "legends" : result.get("legends", {})
    }
    try:
        del result["legends"]["global_rank"]
        del result["legends"]["local_rank"]
    except:
        pass
    if lb_spot is not None:
        try:
            result["legends"]["global_rank"] = lb_spot["global_rank"]
            result["legends"]["local_rank"] = lb_spot["local_rank"]
        except:
            pass
        try:
            result["location"] = lb_spot["country_name"]
        except:
            pass

    return dict(result)


@router.get("/player/{player_tag}/historical/{season}",
         tags=["Player Endpoints"],
         name="Historical data for player events")
@cache(expire=300)
@limiter.limit("30/second")
async def player_historical(player_tag: str, season:str, request: Request, response: Response):
    player_tag = player_tag and "#" + re.sub(r"[^A-Z0-9]+", "", player_tag.upper()).replace("O", "0")
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))
    historical_data = await player_history.find({"$and" : [{"tag": player_tag}, {"time" : {"$gte" : season_start.timestamp()}}, {"time" : {"$lte" : season_end.timestamp()}}]}).sort("time", 1).to_list(length=25000)
    breakdown = defaultdict(list)
    for data in historical_data:
        del data["_id"]
        breakdown[data["type"]].append(data)

    result = {}
    for key, item in breakdown.items():
        result[key] = item

    return dict(result)

@router.get("/player/{player_tag}/warhits",
         tags=["Player Endpoints"],
         name="War attacks done by a player")
@cache(expire=300)
@limiter.limit("30/second")
async def player_warhits(player_tag: str, request: Request, response: Response, limit: int = 200):
    results = await attack_db.find({"tag" : fix_tag(player_tag)}).sort("_time", -1).limit(limit).to_list(length=None)
    if results:
        for result in results:
            del result["_id"]
    return results


@router.get("/player/{player_tag}/legend_rankings",
         tags=["Player Endpoints"],
         name="Previous player legend rankings")
@cache(expire=300)
@limiter.limit("30/second")
async def player_legend_rankings(player_tag: str, request: Request, response: Response, limit:int = 10):

    player_tag = fix_tag(player_tag)
    results = await legend_history.find({"tag": player_tag}).sort("season", -1).limit(limit).to_list(length=None)
    for result in results:
        del result["_id"]

    return results


@router.get("/player/{player_tag}/cache",
         tags=["Player Endpoints"],
         name="Cached endpoint response")
@cache(expire=300)
@limiter.limit("30/second")
async def player_cache(player_tag: str, request: Request, response: Response):
    cache_data = await player_cache_db.find_one({"tag": fix_tag(player_tag)})
    if not cache_data:
        return {"No Player Found" : player_tag}
    return cache_data["data"]


@router.get("/player/search/{name}",
         tags=["Player Endpoints"],
         name="Search for players by name")
@cache(expire=300)
@limiter.limit("30/second")
async def search_players(name: str, request: Request, response: Response):
    pipeline = [
        {
            "$search": {
                "index": "player_search",
                "autocomplete": {
                    "query": name,
                    "path": "name",
                },
            }
        },
        {"$limit": 25}
    ]
    results = await player_search.aggregate(pipeline=pipeline).to_list(length=None)
    for result in results:
        del result["_id"]
    return {"items" : results}


@router.post("/player/bulk",
          tags=["Player Endpoints"],
          name="Cached endpoint response (bulk fetch)")
@limiter.limit("5/second")
async def player_bulk(player_tags: List[str], request: Request, resonse: Response):
    cache_data = await redis.mget(keys=[fix_tag(tag) for tag in player_tags])
    modified_result = {}
    for data in cache_data:
        if data is None:
            continue
        data = ujson.loads(data)
        modified_result[data.get("tag")] = data
    return modified_result