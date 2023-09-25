
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException, APIRouter, Query
from fastapi_cache.decorator import cache
from typing import List, Annotated
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import fix_tag, capital, leagues, clan_cache_db, clan_stats, basic_clan, clan_history, attack_db, clans_db, gen_season_date, player_stats_db, rankings
from bson.objectid import ObjectId
from statistics import mean, median

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Stat Endpoints"])



@router.get("/donations",
         name="Donation Stats")
@cache(expire=300)
@limiter.limit("30/second")
async def donations(request: Request, response: Response,
                           players: Annotated[List[str], Query(max_length=50)]=None,
                           clans: Annotated[List[str], Query(max_length=25)]=None,
                           server: int =None,
                           sort_field: str = "donations",
                           townhalls: Annotated[List[str], Query(max_length=15)]=None,
                           season: str = None,
                           tied_only: bool = True,
                           descending: bool = True,
                           limit: int = 50):
    limit = min(limit, 500)
    season = gen_season_date() if season is None else season
    if server:
        clans = await clans_db.distinct("tag", filter={"server" : server})

    new_data = []
    if players == clans == server == None:
        rank_results = await rankings.find({"donationsRank" : {"$ne" : None}}, {"_id" : 1, "name" : 1, "donations" : 1, "donationsRank" : 1, "donationsReceived" : 1})\
            .sort("donationsRank", 1).limit(limit=limit).to_list(length=None)
        pipeline = [{"$match": {"tag": {"$in": [i.get("_id") for i in rank_results]}}},
                    {"$group": {"_id": "$tag", "th": {"$last": "$townhall"}}}]
        th_results = await attack_db.aggregate(pipeline).to_list(length=None)
        th_results = {item.get("_id"): item.get("th") for item in th_results}
        for r in rank_results:
            new_data.append({
                "rank" : r.get("donationsRank"),
                "name" : r.get("name"),
                "tag" : r.get("_id"),
                "townhall" : th_results.get(r.get("_id")),
                "donations" : r.get("donations"),
                "donationsReceived" : r.get("donationsReceived")
            })
    elif players:
        stat_results = await player_stats_db.find({"tag" : {"$in" : [fix_tag(player) for player in players]}}, {"tag" : 1, "name" : 1, "donations" : 1, "townhall" : 1}).to_list(length=None)
        player_struct = {m.get("tag") : {"tag" : m.get("tag"), "name" : m.get("name"), "rank" : 0,
                                         "donations" : m.get("donations", {}).get(season, {}).get("donated", 0),
                                         "donationsReceived" : m.get("donations", {}).get(season, {}).get("received", 0), "townhall" : m.get("townhall")} for m in stat_results}
        new_data = list(player_struct.values())

    elif clans:
        clan_members = await basic_clan.find({"tag" : {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        member_tags = []
        member_to_name = {}
        for c in clan_members:
            member_list = c.get("memberList", [])
            member_tags += [m.get("tag") for m in member_list]
            for m in member_list:
                member_to_name[m.get("tag")] = m.get("name")
        stat_results = await clan_stats.find({"tag": {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        player_struct = {tag : {"tag" : tag, "name" : member_to_name.get(tag), "rank" : 0, "donations" : 0, "donationsReceived" : 0, "townhall" : 0} for tag in member_tags}
        member_data = await player_stats_db.find({"tag" : {"$in" : member_tags}}, {"tag" : 1, "donations" : 1, "townhall" : 1}).to_list(length=None)
        for member in member_data:
            if not tied_only:
                player_struct[member.get("tag")]["donations"] = member.get("donations", {}).get(season, {}).get("donated", 0)
                player_struct[member.get("tag")]["donationsReceived"] = member.get("donations", {}).get(season, {}).get("received", 0)
            player_struct[member.get("tag")]["townhall"] = member.get("townhall", None)
        if tied_only:
            for result in stat_results:
                this_season = result.get(season)
                if this_season is not None:
                    for tag in member_tags:
                        this_player = this_season.get(tag)
                        if this_player is None:
                            continue
                        player_struct[tag]["donations"] += this_player.get("donated", 0)
                        player_struct[tag]["donationsReceived"] += this_player.get("received", 0)

        new_data = list(player_struct.values())


    totals = {"donations" : 0, "donationsReceived" : 0, "average_townhall" : []}
    for data in new_data:
        totals["donations"] += data.get("donations")
        totals["donationsReceived"] += data.get("donationsReceived")
        if data.get("townhall"):
            totals["average_townhall"].append(data.get("townhall"))
    totals["average_townhall"] = round(mean(totals.get("average_townhall")), 2)

    if townhalls:
        townhalls = [int(th) for th in townhalls if th.isnumeric()]
        new_data = [data for data in new_data if data.get("townhall") in townhalls]

    new_data = sorted(new_data, key=lambda x: x.get(sort_field), reverse=descending)[:limit]
    for count, data in enumerate(new_data, 1):
        data["rank"] = count

    return {"items" : new_data, "totals" : totals,
            "metadata" : {"sort_order" : ("descending" if descending else "ascending"), "sort_field" : sort_field, "season" : season}}




@router.get("/activity",
         name="Activity Stats")
@cache(expire=300)
@limiter.limit("30/second")
async def activity(request: Request, response: Response,
                           players: Annotated[List[str], Query(max_length=50)]=None,
                           clans: Annotated[List[str], Query(max_length=25)]=None,
                           server: int =None,
                           sort_field: str = "activity",
                           townhalls: Annotated[List[str], Query(max_length=15)]=None,
                           season: str = None,
                           tied_only: bool = True,
                           descending: bool = True,
                           limit: int = 50):
    limit = min(limit, 500)
    season = gen_season_date() if season is None else season
    if server:
        clans = await clans_db.distinct("tag", filter={"server" : server})

    new_data = []

    if players:
        stat_results = await player_stats_db.find({"tag" : {"$in" : [fix_tag(player) for player in players]}},
                                                  {"tag" : 1, "name" : 1, "activity" : 1, "townhall" : 1, "last_online" : 1}).to_list(length=None)
        player_struct = {m.get("tag") : {"tag" : m.get("tag"), "name" : m.get("name"), "rank" : 0,
                                         "activity" : m.get("activity", {}).get(season, 0),
                                         "last_online" : m.get("last_online", 0), "townhall" : m.get("townhall", 0)} for m in stat_results}
        new_data = list(player_struct.values())

    elif clans:
        clan_members = await basic_clan.find({"tag" : {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        member_tags = []
        member_to_name = {}
        for c in clan_members:
            member_list = c.get("memberList", [])
            member_tags += [m.get("tag") for m in member_list]
            for m in member_list:
                member_to_name[m.get("tag")] = m.get("name")
        stat_results = await clan_stats.find({"tag": {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        player_struct = {tag : {"tag" : tag, "name" : member_to_name.get(tag), "rank" : 0, "activity" : 0, "last_online" : 0, "townhall" : 0} for tag in member_tags}
        member_data = await player_stats_db.find({"tag" : {"$in" : member_tags}}, {"tag" : 1, "name" : 1, "activity" : 1, "townhall" : 1, "last_online" : 1}).to_list(length=None)
        for member in member_data:
            if not tied_only:
                player_struct[member.get("tag")]["activity"] = member.get("activity", {}).get(season, 0)
            player_struct[member.get("tag")]["last_online"] = member.get("last_online", 0)
            player_struct[member.get("tag")]["townhall"] = member.get("townhall", None)
        if tied_only:
            for result in stat_results:
                this_season = result.get(season)
                if this_season is not None:
                    for tag in member_tags:
                        this_player = this_season.get(tag)
                        if this_player is None:
                            continue
                        player_struct[tag]["activity"] += this_player.get("activity", 0)

        new_data = list(player_struct.values())


    totals = {"total_activity" : 0, "median_activity" : [], "average_townhall" : []}
    for data in new_data:
        totals["total_activity"] += data.get("activity")
        if data.get("townhall"):
            totals["median_activity"].append(data.get("activity"))
            totals["average_townhall"].append(data.get("townhall"))
    totals["median_activity"] = round(median(totals.get("median_activity")), 2)
    totals["average_townhall"] = round(mean(totals.get("average_townhall")), 2)

    if townhalls:
        townhalls = [int(th) for th in townhalls if th.isnumeric()]
        new_data = [data for data in new_data if data.get("townhall") in townhalls]

    new_data = sorted(new_data, key=lambda x: x.get(sort_field), reverse=descending)[:limit]
    for count, data in enumerate(new_data, 1):
        data["rank"] = count

    return {"items" : new_data, "totals" : totals,
            "metadata" : {"sort_order" : ("descending" if descending else "ascending"), "sort_field" : sort_field, "season" : season}}




