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
from .utils import fix_tag, player_history

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Other"])


@router.get("/boost-rate",
         name="Super Troop Boost Rate, for a season (YYYY-MM)")
@cache(expire=300)
@limiter.limit("5/second")
async def super_troop_boost_rate(start_season: str, end_season: str, request: Request, response: Response):
    start_year = start_season[:4]; start_month = start_season[-2:]
    end_year = end_season[:4]; end_month = end_season[-2:]

    SEASON_START = coc.utils.get_season_start(month=int(start_month) - 1, year=int(start_year))
    SEASON_END = coc.utils.get_season_end(month=int(end_month) - 1, year=int(end_year))

    pipeline = [
        {
            "$match": {
                "$and": [
                    {
                        "type": {
                            "$in": coc.enums.SUPER_TROOP_ORDER,
                        },
                    },
                    {
                        "time": {
                            "$gte": SEASON_START.timestamp(),
                        },
                    },
                    {"time" : {
                        "$lte" : SEASON_END.timestamp()
                    }}
                ],
            },
        },
        {
            "$facet": {
                "grouped": [{"$group": {"_id": "$type", "boosts": {"$sum": 1}}}],
                "total": [{"$count": "count"}]
            }
        },
        {
            "$unwind": "$grouped",
        },
        {
            "$unwind": "$total",
        },
        {
            "$set": {
                "usagePercent": {
                    "$multiply": [{"$divide": ["$grouped.boosts", "$total.count"]}, 100],
                },
            },
        },
        {"$set": {"name": "$grouped._id", "boosts": "$grouped.boosts"}},
        {"$unset": ["grouped", "total"]}
    ]
    results = await player_history.aggregate(pipeline=pipeline).to_list(length=None)
    return results





