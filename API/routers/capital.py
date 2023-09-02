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
from .utils import fix_tag, capital

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Clan Capital Endpoints"])

#CLAN CAPITAL ENDPOINTS

#CLAN CAPITAL ENDPOINTS
@router.get("/capital/stats/district",
         tags=["Clan Capital Endpoints"],
         name="Log of Raid Weekends")
#@cache(expire=300)
@limiter.limit("5/second")
async def capital_stats_district(request: Request, response: Response):
    pipeline = [{"$match": {"data.startTime": "20230825T070000.000Z"}},
        {"$unwind": "$data.attackLog"},
        {"$set": {"data": "$data.attackLog"}},
        {"$unwind": "$data.districts"},
        {"$set": {"data": "$data.districts"}},
        {"$unset": ["data.attacks", "_id"]},
         {"$match" : {"data.destructionPercent" : 100}},
         {"$group" : {"_id" : {"district_level" : "$data.districtHallLevel", "district_name" : "$data.name"},
            "average_attacks" : {"$avg" : "$data.attackCount"},
            "sample_size" : {"$sum" : "$data.attackCount"},
            "min_attacks" : {"$min" : "$data.attackCount"},
            "max_attacks" : {"$max" : "$data.attackCount"},
            "99_percentile": {"$percentile" : {"input" : "$data.attackCount", "p" : [0.01], "method" : "approximate"}},
            "95_percentile": {"$percentile": {"input": "$data.attackCount", "p": [0.05], "method": "approximate"}},
            "75_percentile": {"$percentile": {"input": "$data.attackCount", "p": [0.25], "method": "approximate"}},
            "50_percentile": {"$percentile": {"input": "$data.attackCount", "p": [0.5], "method": "approximate"}},
            "25_percentile": {"$percentile": {"input": "$data.attackCount", "p": [0.75], "method": "approximate"}},
            "5_percentile": {"$percentile": {"input": "$data.attackCount", "p": [0.95], "method": "approximate"}},
            "standardDeviation" : {"$stdDevPop" : "$data.attackCount"}
             }},
        {"$sort": {"_id.district_name": 1, "_id.district_level": 1}}
    ]
    results = await capital.aggregate(pipeline=pipeline).to_list(length=None)
    return results



@router.get("/capital/{clan_tag}",
         tags=["Clan Capital Endpoints"],
         name="Log of Raid Weekends")
@cache(expire=300)
@limiter.limit("30/second")
async def capital_log(clan_tag: str, request: Request, response: Response):
    results = await capital.find({"clan_tag" : fix_tag(clan_tag)}).to_list(length=None)
    for result in results:
        del result["_id"]
    return results

@router.post("/capital/bulk",
         tags=["Clan Capital Endpoints"],
         name="Fetch Raid Weekends in Bulk (max 100 tags)")
@limiter.limit("5/second")
async def capital_bulk(clan_tags: List[str], request: Request, response: Response):
    results = await capital.find({"clan_tag": {"$in" : [fix_tag(tag) for tag in clan_tags[:100]]}}).to_list(length=None)
    fixed_results = defaultdict(list)
    for result in results:
        del result["_id"]
        tag = result.get("clan_tag")
        del result["clan_tag"]
        fixed_results[tag].append(result.get("data"))
    return dict(fixed_results)