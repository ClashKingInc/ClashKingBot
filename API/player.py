import datetime
import re

import pytz
import ujson
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from APIUtils.utils import fix_tag, redis, db_client
from datetime import timedelta

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Player Endpoints"])


@router.get("/player/{player_tag}/stats",
         tags=["Player Endpoints"],
         name="All collected Stats for a player (clan games, looted, activity, etc)")
@cache(expire=300)
@limiter.limit("30/second")
async def player_stat(player_tag: str, request: Request, response: Response):
    player_tag = player_tag and "#" + re.sub(r"[^A-Z0-9]+", "", player_tag.upper()).replace("O", "0")
    result = await db_client.player_stats_db.find_one({"tag": player_tag})
    lb_spot = await db_client.player_leaderboard_db.find_one({"tag": player_tag})

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
        "legends" : result.get("legends", {}),
        "last_online" : result.get("last_online"),
        "looted" : {"gold": result.get("gold", {}), "elixir": result.get("elixir", {}), "dark_elixir": result.get("dark_elixir", {})},
        "trophies" : result.get("trophies", 0),
        "warStars" : result.get("warStars"),
        "clanCapitalContributions" : result.get("aggressive_capitalism"),
        "donations": result.get("donations", {}),
        "capital" : result.get("capital_gold", {}),
        "clan_games" : result.get("clan_games", {}),
        "season_pass" : result.get("season_pass", {}),
        "attack_wins" : result.get("attack_wins", {}),
        "activity" : result.get("activity", {}),
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
async def player_legend(player_tag: str, request: Request, response: Response, season: str = None):
    player_tag = fix_tag(player_tag)

    result = await db_client.player_stats_db.find_one({"tag": player_tag})
    if result is None:
        raise HTTPException(status_code=404, detail=f"No player found")

    ranking_data = await db_client.player_leaderboard_db.find_one({"tag": player_tag}, projection={"_id" : 0})
    default = {"country_code": None,
               "country_name": None,
               "local_rank": None,
               "global_rank": None}
    if ranking_data is None:
        ranking_data = default
    if ranking_data.get("global_rank") is None:
        self_global_ranking = await db_client.legend_rankings.find_one({"tag": player_tag})
        if self_global_ranking:
            ranking_data["global_rank"] = self_global_ranking.get("rank")

    legend_data = result.get('legends', {})
    if season and legend_data != {}:
        year, month = season.split("-")
        season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
        season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))
        delta = season_end - season_start
        days = [season_start + timedelta(days=i) for i in range(delta.days)]
        days = [day.strftime("%Y-%m-%d") for day in days]

        _holder = {}
        for day in days:
            _holder[day] = legend_data.get(day)
        legend_data = _holder

    result = {
        "name" : result.get("name"),
        "townhall" : result.get("townhall"),
        "legends" : legend_data,
        "rankings" : ranking_data
    }
    result["legends"].pop("global_rank")
    result["legends"].pop("local_rank")
    result["streak"] = result["legends"].pop("streak", 0)
    return result


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
    historical_data = await db_client.player_history.find({"$and" : [{"tag": player_tag}, {"time" : {"$gte" : season_start.timestamp()}}, {"time" : {"$lte" : season_end.timestamp()}}]}).sort("time", 1).to_list(length=25000)
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
         name="War attacks done/defended by a player")
@cache(expire=300)
@limiter.limit("30/second")
async def player_warhits(player_tag: str, request: Request, response: Response):
    player_tag = fix_tag(player_tag)
    pipeline = [
        {"$match": {"$or": [{"data.clan.members.tag": player_tag}, {"data.opponent.members.tag": player_tag}]}},
        {"$unset": ["_id"]},
        {"$project": {"data": "$data"}}
    ]
    wars = await db_client.clan_wars.aggregate(pipeline, allowDiskUse=True).to_list(length=None)
    found_wars = set()
    stats = {"attacks" : [], "defenses" : []}
    for war in wars:
        war = war.get("data")
        war = coc.ClanWar(data=war, client=None)
        war_unique_id = "-".join(sorted([war.clan_tag, war.opponent.tag])) + f"-{int(war.preparation_start_time.time.timestamp())}"
        if war_unique_id in found_wars:
            continue
        found_wars.add(war_unique_id)
        war_member = war.get_member(player_tag)
        for attack in war_member.attacks:
            stats["attacks"].append({
                "tag": attack.attacker.tag,
                "name": attack.attacker.name,
                "townhall": attack.attacker.town_hall,
                "destruction": attack.destruction,
                "stars": attack.stars,
                "fresh": attack.is_fresh_attack,
                "war_start": int(war.preparation_start_time.time.timestamp()),
                "defender_tag": attack.defender.tag,
                "defender_name": attack.defender.name,
                "defender_townhall": attack.defender.town_hall,
                "war_type": str(war.type),
                "war_status": str(war.status),
                "attack_order": attack.order,
                "map_position": attack.attacker.map_position,
                "war_size": war.team_size,
                "clan": attack.attacker.clan.tag,
                "clan_name": attack.attacker.clan.name,
                "defending_clan": attack.defender.clan.tag,
                "defending_clan_name": attack.defender.clan.name,
            })
        for attack in war_member.defenses:
            stats["defenses"].append({
                "tag": attack.attacker.tag,
                "name": attack.attacker.name,
                "townhall": attack.attacker.town_hall,
                "destruction": attack.destruction,
                "stars": attack.stars,
                "fresh": attack.is_fresh_attack,
                "war_start": int(war.preparation_start_time.time.timestamp()),
                "defender_tag": attack.defender.tag,
                "defender_name": attack.defender.name,
                "defender_townhall": attack.defender.town_hall,
                "war_type": str(war.type),
                "war_status": str(war.status),
                "attack_order": attack.order,
                "map_position": attack.attacker.map_position,
                "war_size": war.team_size,
                "clan": attack.attacker.clan.tag,
                "clan_name": attack.attacker.clan.name,
                "defending_clan": attack.defender.clan.tag,
                "defending_clan_name": attack.defender.clan.name,
            })

    return stats


@router.get("/player/{player_tag}/legend_rankings",
         tags=["Player Endpoints"],
         name="Previous player legend rankings")
@cache(expire=300)
@limiter.limit("30/second")
async def player_legend_rankings(player_tag: str, request: Request, response: Response, limit:int = 10):

    player_tag = fix_tag(player_tag)
    results = await db_client.legend_history.find({"tag": player_tag}).sort("season", -1).limit(limit).to_list(length=None)
    for result in results:
        del result["_id"]

    return results


@router.get("/player/{player_tag}/wartimer",
         tags=["Player Endpoints"],
         name="Get the war timer for a player")
@cache(expire=300)
@limiter.limit("30/second")
async def player_wartimer(player_tag: str, request: Request, response: Response):
    player_tag = fix_tag(player_tag)
    result = await db_client.war_timer.find_one({"_id" : player_tag})
    if result is None:
        return result
    result["tag"] = result.pop("_id")
    time: datetime.datetime = result["time"]
    time = time.replace(tzinfo=pytz.utc)
    result["unix_time"] = time.timestamp()
    result["time"] = time.isoformat()
    return result


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
    results = await db_client.player_search.aggregate(pipeline=pipeline).to_list(length=None)
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