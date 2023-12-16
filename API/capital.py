
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from APIUtils.utils import fix_tag, db_client, leagues
from datetime import datetime


limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Clan Capital Endpoints"])


#CLAN CAPITAL ENDPOINTS
@router.get("/capital/stats/district",
         tags=["Clan Capital Endpoints"],
         name="Stats about districts, (weekend: YYYY-MM-DD)")
@cache(expire=8000000)
@limiter.limit("30/second")
async def capital_stats_district(weekend: str, request: Request, response: Response):
    weekend_to_iso = datetime.strptime(weekend, "%Y-%m-%d")
    if (datetime.now() - weekend_to_iso).total_seconds() <= 273600:
        raise HTTPException(status_code=404, detail=f"Please wait until 4 hours after Raid Weekend is completed to collect stats")
    weekend_to_iso = weekend_to_iso.replace(hour=7)
    weekend = weekend_to_iso.strftime('%Y%m%dT%H%M%S.000Z')
    pipeline = [{"$match": {"data.startTime": weekend}},
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
    results = await db_client.capital.aggregate(pipeline=pipeline).to_list(length=None)
    return results

@router.get("/capital/stats/leagues",
         tags=["Clan Capital Endpoints"],
         name="Stats about capital leagues, (weekend: YYYY-MM-DD")
@cache(expire=8000000)
@limiter.limit("30/second")
async def capital_stats_leagues(weekend: str, request: Request, response: Response):
    og_weekend = weekend
    weekend_to_iso = datetime.strptime(weekend, "%Y-%m-%d")
    if (datetime.now() - weekend_to_iso).total_seconds() <= 273600:
        raise HTTPException(status_code=404, detail=f"Please wait until 4 hours after Raid Weekend is completed to collect stats")
    weekend_to_iso = weekend_to_iso.replace(hour=7)
    weekend = weekend_to_iso.strftime('%Y%m%dT%H%M%S.000Z')
    pipeline = [
    {
        '$match': {
            "$and" : [{'data.startTime': weekend}, {"data.totalAttacks" : {"$gte" : 1}}]
        }
    }, {
        '$addFields': {
          'topCapitalGoldRaided': {
                '$max': '$data.members.capitalResourcesLooted'
            },
          "leastCapitalGoldRaided" : {"$min" : "$data.members.capitalResourcesLooted"},
          'raidMedals': {
                '$add': [
                    {
                        '$multiply': [
                            '$data.offensiveReward', 6
                        ]
                    }, '$data.defensiveReward'
                ]
            },
          "averageAttacksDone" : {"$divide" : [{"$sum" : "$data.members.attacks"}, {"$size" : "$data.members"}]},
          "totalCapitalGoldLooted" : "$data.capitalTotalLoot",
          "numMembers" : {"$size" : "$data.members"},
          "sixHitMembers" : {"$size" : {"$filter" : {"input" : "$data.members", "as": "v", "cond" : {"$eq" : ["$$v.attacks", 6]}}}},
          "districtsDestroyed" : {"$sum": "$data.attackLog.districtsDestroyed"},
          "raidsDone" : {"$size" : "$data.attackLog"},
          "raidsTaken" : {"$size" : "$data.defenseLog"}
        }
        }, {
        '$unset': [
            '_id', "data"
        ]
    }, {
        '$lookup': {
            'from': 'clan_tags',
            'localField': 'clan_tag',
            'foreignField': 'tag',
            'as': 'league'
        }
    }, {
        '$set': {
            'league': {
                '$first': f'$league.changes.clanCapital.{og_weekend}.league'
            }
        }
    },
  {"$match" : {"league" : {"$ne" : None}}},
  {"$group" : {"_id" : "$league", "averageAttacksDone" : {"$avg" : "$averageAttacksDone"},
              "averageNumMembers" : {"$avg" : "$numMembers"},
              "averageSixHitMembers" : {"$avg" : "$sixHitMembers"},
              "avgRaidsDone" : {"$avg" : "$raidsDone"},
              "avgRaidsTaken" : {"$avg" : "$raidsTaken"},
              "avgDistrictsDestroyed" : {"$avg" : "$districtsDestroyed"},
              "avgRaidMedals" : {"$avg" : "$raidMedals"},
              "topRaidMedals" : {"$max" : "$raidMedals"},
              "avgTopCapitalGoldRaided" : {"$avg" : "$topCapitalGoldRaided"},
              "topCapitalGoldRaided" : {"$max" : "$topCapitalGoldRaided"},
              "sampleSize" : {"$sum" : 1}
              }},
    ]
    results = await db_client.capital.aggregate(pipeline=pipeline).to_list(length=None)
    results.sort(key=lambda val : leagues.index(val.get("_id")))
    return results



@router.get("/capital/{clan_tag}",
         tags=["Clan Capital Endpoints"],
         name="Log of Raid Weekends")
@cache(expire=300)
@limiter.limit("30/second")
async def capital_log(clan_tag: str, request: Request, response: Response, limit: int = 5):
    results = await db_client.capital.find({"clan_tag" : fix_tag(clan_tag)}).limit(limit).sort("data.startTime", -1).to_list(length=None)
    for result in results:
        del result["_id"]
    return results

@router.post("/capital/bulk",
         tags=["Clan Capital Endpoints"],
         name="Fetch Raid Weekends in Bulk (max 100 tags)")
@limiter.limit("5/second")
async def capital_bulk(clan_tags: List[str], request: Request, response: Response):
    results = await db_client.capital.find({"clan_tag": {"$in" : [fix_tag(tag) for tag in clan_tags[:100]]}}).to_list(length=None)
    fixed_results = defaultdict(list)
    for result in results:
        del result["_id"]
        tag = result.get("clan_tag")
        del result["clan_tag"]
        fixed_results[tag].append(result.get("data"))
    return dict(fixed_results)