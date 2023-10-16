import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List, Union
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import fix_tag, capital, leagues, player_trophies, player_versus_trophies, clan_trophies, capital_trophies, clan_versus_trophies


limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Leaderboard History"])

@router.get("/ranking/player-trophies/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def player_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await player_trophies.find_one({"$and" : [{"location" : location}, {"date" : date}]})
    return r.get("data")


@router.get("/ranking/player-builder/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def player_builder_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await player_versus_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@router.get("/ranking/clan-trophies/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await clan_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@router.get("/ranking/clan-builder/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_builder_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await clan_versus_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@router.get("/ranking/clan-capital/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_capital_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await capital_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")