
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException, APIRouter, Query
from fastapi_cache.decorator import cache
from typing import List, Annotated
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from APIUtils.utils import fix_tag, db_client, gen_season_date, gen_games_season, gen_raid_date
from statistics import mean, median
from datetime import datetime, timedelta
from pytz import utc
from dotenv import load_dotenv
load_dotenv()

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Stat Endpoints"])

coc_client= coc.Client(key_names="keys for my windows pc", key_count=5, raw_attribute=True)


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
        clans = await db_client.clans_db.distinct("tag", filter={"server" : server})

    new_data = []
    clan_to_name = {}
    by_clan = defaultdict(lambda : defaultdict(int))
    field_to_use = "donations" if sort_field != "donationsReceived" else "donationsReceived"

    if players == clans == server == None:
        rank_results = await db_client.rankings.find({"donationsRank" : {"$ne" : None}}, {"_id" : 1, "name" : 1, "donations" : 1, "donationsRank" : 1, "donationsReceived" : 1})\
            .sort("donationsRank", 1).limit(limit=limit).to_list(length=None)
        pipeline = [{"$match": {"tag": {"$in": [i.get("_id") for i in rank_results]}}},
                    {"$group": {"_id": "$tag", "th": {"$last": "$townhall"}}}]
        th_results = await db_client.attack_db.aggregate(pipeline).to_list(length=None)
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
            stat_results = await db_client.player_stats_db.find({"tag": {"$in": [fix_tag(player) for player in players]}},
                                                      {"tag": 1, "name": 1, "donations": 1, "townhall": 1, "clan_tag": 1}).to_list(length=None)
            player_struct = {m.get("tag"): {"tag": m.get("tag"), "name": m.get("name"), "rank": 0,
                                            "donations": m.get("donations", {}).get(season, {}).get("donated", 0),
                                            "donationsReceived": m.get("donations", {}).get(season, {}).get("received", 0), "townhall": m.get("townhall"),
                                            "clan_tag": m.get("clan_tag")} for m in stat_results}
            for tag in players:
                tag = fix_tag(tag)
                p_results = await db_client.clan_stats.find({f"{season}.{tag}" : {"$ne" : None}}, {f"{season}.{tag}" : 1, "tag" : 1}).to_list(length=None)
                for result in p_results:
                    by_clan[result.get("tag")][field_to_use] += result.get(season).get(tag).get("received" if field_to_use != "donations" else "donated", 0)

            new_data = list(player_struct.values())

    elif clans:
        clan_members = await db_client.basic_clan.find({"tag" : {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        clan_to_name = {c.get("tag") : c.get("name") for c in clan_members}
        member_tags = []
        member_to_name = {}
        member_to_clan_tag = {}
        for c in clan_members:
            member_list = c.get("memberList", [])
            member_tags += [m.get("tag") for m in member_list]
            for m in member_list:
                member_to_clan_tag[m.get("tag")] = c.get("tag")
                member_to_name[m.get("tag")] = m.get("name")
        stat_results = await db_client.clan_stats.find({"tag": {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        player_struct = {tag : {"tag" : tag, "name" : member_to_name.get(tag), "rank" : 0, "donations" : 0, "donationsReceived" : 0, "townhall" : 0, "clan_tag" : None} for tag in member_tags}
        member_data = await db_client.player_stats_db.find({"tag" : {"$in" : member_tags}}, {"tag" : 1, "donations" : 1, "townhall" : 1}).to_list(length=None)
        for member in member_data:
            if not tied_only:
                player_struct[member.get("tag")]["donations"] = member.get("donations", {}).get(season, {}).get("donated", 0)
                player_struct[member.get("tag")]["donationsReceived"] = member.get("donations", {}).get(season, {}).get("received", 0)
                by_clan[member_to_clan_tag.get(member.get("tag"))][field_to_use] += member.get("donations", {}).get(season, {}).get("donated" if field_to_use != "donationsReceived" else "received", 0)
            player_struct[member.get("tag")]["townhall"] = member.get("townhall", None)

        for result in stat_results:
            clan_tag = result.get("tag")
            this_season = result.get(season)
            if this_season is not None:
                for tag in member_tags:
                    this_player = this_season.get(tag)
                    if this_player is None:
                        continue
                    player_struct[tag]["clan_tag"] = clan_tag
                    if not tied_only:
                        continue
                    by_clan[clan_tag][field_to_use] += this_player.get("donated" if field_to_use != "donationsReceived" else "received", 0)
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

    print()
    by_clan_totals = []
    if not clan_to_name:
        print("ere")
        clan_results = await db_client.basic_clan.find({"tag": {"$in": list(by_clan.keys())}}).to_list(length=None)
        clan_to_name = {c.get("tag"): c.get("name") for c in clan_results}
    print(clan_to_name)
    for k, v in by_clan.items():
        print("here")
        if clan_to_name.get(k) is None:
            continue
        by_clan_totals.append({"tag": k, "name": clan_to_name.get(k), field_to_use: v.get(field_to_use)})

    return {"items" : new_data, "totals" : totals,"clan_totals" : by_clan_totals,
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
        clans = await db_client.clans_db.distinct("tag", filter={"server" : server})

    new_data = []
    clan_to_name = {}
    by_clan = defaultdict(lambda : defaultdict(int))

    if players:
        stat_results = await db_client.player_stats_db.find({"tag" : {"$in" : [fix_tag(player) for player in players]}},
                                                  {"tag" : 1, "name" : 1, "activity" : 1, "townhall" : 1, "last_online" : 1, "clan_tag" : 1}).to_list(length=None)
        player_struct = {m.get("tag") : {"tag" : m.get("tag"), "name" : m.get("name"), "rank" : 0,
                                         "activity" : m.get("activity", {}).get(season, 0),
                                         "last_online" : m.get("last_online", 0) if m.get("last_online") is not None else 0,
                                         "townhall" : m.get("townhall", 0), "clan_tag" : m.get("clan_tag")} for m in stat_results}
        new_data = list(player_struct.values())
        for data in new_data:
            by_clan[data.get("clan_tag")]["activity"] += data.get("activity")
    elif clans:
        clan_members = await db_client.basic_clan.find({"tag" : {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        clan_to_name = {c.get("tag") : c.get("name") for c in clan_members}
        member_tags = []
        member_to_name = {}
        for c in clan_members:
            member_list = c.get("memberList", [])
            member_tags += [m.get("tag") for m in member_list]
            for m in member_list:
                member_to_name[m.get("tag")] = m.get("name")
        stat_results = await db_client.clan_stats.find({"tag": {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        player_struct = {tag : {"tag" : tag, "name" : member_to_name.get(tag), "rank" : 0, "activity" : 0, "last_online" : 0, "townhall" : 0} for tag in member_tags}
        member_data = await db_client.player_stats_db.find({"tag" : {"$in" : member_tags}}, {"tag" : 1, "name" : 1, "activity" : 1, "townhall" : 1, "last_online" : 1, "clan_tag" : None}).to_list(length=None)
        for member in member_data:
            if not tied_only:
                player_struct[member.get("tag")]["activity"] = member.get("activity", {}).get(season, 0)
            player_struct[member.get("tag")]["last_online"] = member.get("last_online", 0) if member.get("last_online") is not None else 0
            player_struct[member.get("tag")]["townhall"] = member.get("townhall", None)
        for result in stat_results:
            clan_tag = result.get("tag")
            this_season = result.get(season)
            if this_season is not None:
                for tag in member_tags:
                    this_player = this_season.get(tag)
                    if this_player is None:
                        continue
                    player_struct[tag]["clan_tag"] = clan_tag
                    if not tied_only:
                        continue
                    by_clan[clan_tag]["activity"] += this_player.get("activity", 0)
                    player_struct[tag]["activity"] += this_player.get("activity", 0)

        new_data = list(player_struct.values())


    totals = {"activity" : 0, "median_activity" : [], "average_townhall" : []}
    for data in new_data:
        totals["activity"] += data.get("activity")
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

    by_clan_totals = []
    if not clan_to_name:
        clan_results = await db_client.basic_clan.find({"tag": {"$in": list(by_clan.keys())}}).to_list(length=None)
        clan_to_name = {c.get("tag"): c.get("name") for c in clan_results}
    for k, v in by_clan.items():
        if clan_to_name.get(k) is None:
            continue
        by_clan_totals.append({"tag": k, "name": clan_to_name.get(k), "activity": v.get("activity")})

    return {"items" : new_data, "totals" : totals, "clan_totals" : by_clan_totals,
            "metadata" : {"sort_order" : ("descending" if descending else "ascending"), "sort_field" : sort_field, "season" : season}}


@router.get("/clan-games",
         name="Clan Game Stats")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_games(request: Request, response: Response,
                           players: Annotated[List[str], Query(max_length=50)]=None,
                           clans: Annotated[List[str], Query(max_length=25)]=None,
                           server: int =None,
                           sort_field: str = "points",
                           townhalls: Annotated[List[str], Query(max_length=15)]=None,
                           season: str = None,
                           tied_only: bool = True,
                           descending: bool = True,
                           limit: int = 50):
    limit = min(limit, 500)
    season = gen_games_season() if season is None else season
    if server:
        clans = await db_client.clans_db.distinct("tag", filter={"server" : server})
    check_time = int(datetime.now().timestamp())
    current_season = gen_season_date()
    if season != current_season:
        split_season = season.split("-")
        check_time  = int(datetime(int(split_season[0]), int(split_season[1]), 28, hour=8, tzinfo=utc).timestamp())

    year = int(season[:4])
    month = int(season[-2:])
    next_month = month + 1
    if month == 12:
        next_month = 1
        year += 1
    start = datetime(year, month, 1)
    end = datetime(year, next_month, 1)
    new_data = []
    clan_to_name = {}
    by_clan = defaultdict(lambda : defaultdict(int))

    if players:
        pipeline = [
            {"$match": {"$and": [{"tag": {"$in": [fix_tag(player) for player in players]}}, {"type": "Games Champion"},
                                 {"time": {"$gte": start.timestamp()}},
                                 {"time": {"$lte": end.timestamp()}}]}},
            {"$sort": {"tag": 1, "time": 1}},
            {"$group": {"_id": "$tag", "first": {"$first": "$time"}, "last": {"$last": "$time"}}}
        ]
        results: List[dict] = await db_client.player_history.aggregate(pipeline).to_list(length=None)
        member_stat_dict = {}
        for m in results:
            member_stat_dict[m["_id"]] = {"first": m["first"], "last": m["last"]}
        stat_results = await db_client.player_stats_db.find({"tag" : {"$in" : [fix_tag(player) for player in players]}},
                                                  {"tag" : 1, "name" : 1, "clan_games" : 1, "townhall" : 1, "clan_tag" : 1}).to_list(length=None)
        player_struct = {m.get("tag") : {"tag" : m.get("tag"), "name" : m.get("name"), "rank" : 0,
                                         "points" : m.get("clan_games", {}).get(season, {}).get("points", 0),
                                         "time_taken" : 0, "townhall" : m.get("townhall", 0), "clan_tag" : m.get("clan_tag")} for m in stat_results}
        for tag, value in player_struct.items():
            points = value.get("points")
            stats = member_stat_dict.get(tag)
            if stats is not None:
                if points < 4000:
                    stats["last"] = check_time
                first_time = datetime.fromtimestamp(stats["first"])
                last_time = datetime.fromtimestamp(stats["last"])
                player_struct[tag]["time_taken"] = (last_time - first_time).seconds
        new_data = list(player_struct.values())
        for data in new_data:
            by_clan[data.get("clan_tag")]["points"] += data.get("points")

    elif clans:
        clan_members = await db_client.basic_clan.find({"tag" : {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        clan_to_name = {c.get("tag") : c.get("name") for c in clan_members}
        member_tags = []
        member_to_name = {}
        tag_to_clan = {}
        for c in clan_members:
            member_list = c.get("memberList", [])
            member_tags += [m.get("tag") for m in member_list]
            for m in member_list:
                member_to_name[m.get("tag")] = m.get("name")
                tag_to_clan[m.get("tag")] = c.get("tag")
        pipeline = [
            {"$match": {"$and": [{"tag": {"$in": member_tags}}, {"type": "Games Champion"},
                                 {"time": {"$gte": start.timestamp()}},
                                 {"time": {"$lte": end.timestamp()}}]}},
            {"$sort": {"tag": 1, "time": 1}},
            {"$group": {"_id": "$tag", "first": {"$first": "$time"}, "last": {"$last": "$time"}}}
        ]
        results: List[dict] = await db_client.player_history.aggregate(pipeline).to_list(length=None)
        member_stat_dict = {}
        for m in results:
            member_stat_dict[m["_id"]] = {"first": m["first"], "last": m["last"]}
        stat_results = await db_client.clan_stats.find({"tag": {"$in" : [fix_tag(clan) for clan in clans]}}).to_list(length=None)
        player_struct = {tag : {"tag" : tag, "name" : member_to_name.get(tag), "rank" : 0, "points" : 0, "time_taken" : 0, "townhall" : 0, "clan_tag": None} for tag in member_tags}
        member_data = await db_client.player_stats_db.find({"tag" : {"$in" : member_tags}}, {"tag" : 1, "name" : 1, "clan_games" : 1, "townhall" : 1}).to_list(length=None)
        for member in member_data:
            if not tied_only:
                player_struct[member.get("tag")]["points"] = member.get("clan_games", {}).get(season, {}).get("points", 0)
            player_struct[member.get("tag")]["townhall"] = member.get("townhall", None)
        for result in stat_results:
            clan_tag = result.get("tag")
            this_season = result.get(season)
            if this_season is not None:
                for tag in member_tags:
                    this_player = this_season.get(tag)
                    if this_player is None:
                        continue
                    player_struct[tag]["clan_tag"] = clan_tag
                    if not tied_only:
                        continue
                    by_clan[clan_tag]["points"] += this_player.get("clan_games", 0)
                    player_struct[tag]["points"] += this_player.get("clan_games", 0)

        for tag, value in player_struct.items():
            points = value.get("points")
            if points == 0:
                continue
            stats = member_stat_dict.get(tag)
            if stats is not None:
                if points < 4000:
                    stats["last"] = check_time
                first_time = datetime.fromtimestamp(stats["first"])
                last_time = datetime.fromtimestamp(stats["last"])
                player_struct[tag]["time_taken"] = (last_time - first_time).seconds
        new_data = list(player_struct.values())


    totals = {"points" : 0, "average_points" : [], "average_townhall" : []}
    for data in new_data:
        totals["points"] += data.get("points")
        if data.get("townhall"):
            totals["average_points"].append(data.get("points"))
            totals["average_townhall"].append(data.get("townhall"))
    totals["average_points"] = round(mean(totals.get("average_points")), 2)
    totals["average_townhall"] = round(mean(totals.get("average_townhall")), 2)

    if townhalls:
        townhalls = [int(th) for th in townhalls if th.isnumeric()]
        new_data = [data for data in new_data if data.get("townhall") in townhalls]

    if sort_field == "time_taken":
        new_data = [data for data in new_data if data.get("points") != 0]
        new_data = sorted(new_data, key=lambda x: (x.get("points") >= 4000, -x.get(sort_field) if x.get(sort_field) != 0 else 999999999), reverse=descending)[:limit]
    else:
     new_data = sorted(new_data, key=lambda x: x.get(sort_field), reverse=descending)[:limit]
    for count, data in enumerate(new_data, 1):
        data["rank"] = count

    by_clan_totals = []
    if not clan_to_name:
        clan_results = await db_client.basic_clan.find({"tag" : {"$in" : list(by_clan.keys())}}).to_list(length=None)
        clan_to_name = {c.get("tag"): c.get("name") for c in clan_results}
    for k, v in by_clan.items():
        if clan_to_name.get(k) is None:
            continue
        by_clan_totals.append({"tag" : k, "name" : clan_to_name.get(k), "points" : v.get("points")})
    return {"items" : new_data, "totals" : totals, "clan_totals" : by_clan_totals,
            "metadata" : {"sort_order" : ("descending" if descending else "ascending"), "sort_field" : sort_field, "season" : season}}


@router.get("/war-stats",
         name="War Stats")
@cache(expire=300)
@limiter.limit("10/second")
async def war_stats(request: Request, response: Response,
                           players: Annotated[List[str], Query(max_length=50)]=None,
                           clans: Annotated[List[str], Query(max_length=25)]=None,
                           server: int =None,
                           sort_field: str = "hit_rates.hitrate",
                           townhalls: Annotated[List[str], Query(max_length=15)]=None,
                           season_or_timestamp: str = None,
                           tied_only: bool = True,
                           descending: bool = True,
                           limit: int = 50):

    limit = min(limit, 500)
    if server:
        clans = await db_client.clans_db.distinct("tag", filter={"server" : server})

    if season_or_timestamp is None:
        season_or_timestamp = gen_season_date()
    if not season_or_timestamp.isnumeric():
        year = season_or_timestamp[:4]
        month = season_or_timestamp[-2:]
        SEASON_START = coc.utils.get_season_start(month=(int(month) - 1 if int(month) != 1 else month == 12), year=int(year) if int(month) != 1 else int(year)-1).timestamp()
        SEASON_END = coc.utils.get_season_end(month=(int(month) - 1 if int(month) != 1 else month == 12), year=int(year) if int(month) != 1 else int(year)-1).timestamp()
    else:
        SEASON_START = int(season_or_timestamp)
        SEASON_END = int(datetime.now().timestamp())

    SEASON_START = datetime.fromtimestamp(SEASON_START, tz=utc).strftime('%Y%m%dT%H%M%S.000Z')
    SEASON_END = datetime.fromtimestamp(SEASON_END, tz=utc).strftime('%Y%m%dT%H%M%S.000Z')

    clan_to_name = {}
    by_clan = defaultdict(lambda : defaultdict(int))
    if not tied_only:
        basic_clans = await db_client.basic_clan.find({"tag": {"$in" : clans}}).to_list(length=None)
        players = []
        for b_c in basic_clans:
            players += [m.get("tag") for m in b_c.get("memberList", [])]

    player_stats = []
    player_attacks = defaultdict(list)
    player_defenses = defaultdict(list)
    if players:
        pipeline = [
            {"$match" : {"$and" : [{"$or" : [{"data.clan.members.tag" : {"$in" : players}}, {"data.opponent.members.tag" : {"$in" : players}}]},
                        {"data.preparationStartTime" : {"$gte" : SEASON_START}}, {"data.preparationStartTime" : {"$lte" : SEASON_END}}]}},
            {"$unset": ["_id"]},
            {"$project": {"data" : "$data"}}
        ]
        wars = await db_client.clan_wars.aggregate(pipeline, allowDiskUse=True).to_list(length=None)
        found_wars = set()
        for war in wars:
            war = war.get("data")
            war = coc.ClanWar(data=war, client=coc_client)
            war_unique_id = "-".join(sorted([war.clan_tag, war.opponent.tag])) + f"-{int(war.preparation_start_time.time.timestamp())}"
            if war_unique_id in found_wars:
                continue
            found_wars.add(war_unique_id)
            for tag in players:
                war_member = war.get_member(tag)
                for attack in war_member.attacks:
                    player_attacks[tag].append({
                        "tag": attack.attacker.tag,
                        "name": attack.attacker.name,
                        "townhall": attack.attacker.town_hall,
                        "destruction": attack.destruction,
                        "stars": attack.stars,
                        "fresh": attack.is_fresh_attack,
                        "_time": int(war.end_time.time.timestamp()),
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
                    player_defenses[tag].append({
                        "tag": attack.attacker.tag,
                        "name": attack.attacker.name,
                        "townhall": attack.attacker.town_hall,
                        "destruction": attack.destruction,
                        "stars": attack.stars,
                        "fresh": attack.is_fresh_attack,
                        "_time": int(war.end_time.time.timestamp()),
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

    elif clans:
        pipeline = [
            {"$match": {"$and": [{"$or": [{"clan": {"$in": clans}}, {"opponent": {"$in": clans}}]},
                                 {"data.preparationStartTime": {"$gte": SEASON_START}}, {"data.preparationStartTime": {"$lte": SEASON_END}}]}},
            {"$unset": ["_id"]},
            {"$project": {"data": "$data"}}
        ]
        wars: List[dict] = await db_client.clan_wars.aggregate(pipeline, allowDiskUse=True).to_list(length=None)
        found_wars = set()
        for war in wars:
            war = war.get("data")
            war = coc.ClanWar(data=war, client=coc_client)
            war_unique_id = "-".join(sorted([war.clan_tag, war.opponent.tag])) + f"-{int(war.preparation_start_time.time.timestamp())}"
            if war_unique_id in found_wars:
                continue
            found_wars.add(war_unique_id)
            war_sides = []
            if war.clan_tag in clans:
                war_sides.append(war.clan)
            if war.opponent.tag in clans:
                war_sides.append(war.opponent)
            for side in war_sides:
                for attack in side.attacks:
                    player_attacks[attack.attacker_tag].append({
                        "tag": attack.attacker.tag,
                        "name": attack.attacker.name,
                        "townhall": attack.attacker.town_hall,
                        "destruction": attack.destruction,
                        "stars": attack.stars,
                        "fresh": attack.is_fresh_attack,
                        "_time": int(war.end_time.time.timestamp()),
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
                for attack in side.defenses:
                    player_defenses[attack.defender_tag].append({
                        "tag": attack.attacker.tag,
                        "name": attack.attacker.name,
                        "townhall": attack.attacker.town_hall,
                        "destruction": attack.destruction,
                        "stars": attack.stars,
                        "fresh": attack.is_fresh_attack,
                        "_time": int(war.end_time.time.timestamp()),
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

        players = list(player_attacks.keys()) + list(player_defenses.keys())


    for tag in players:
        this_player_attacks = player_attacks.get(tag, [])
        this_player_defenses = player_defenses.get(tag, [])
        if not this_player_attacks and not this_player_defenses:
            continue
        use = this_player_attacks
        if not this_player_attacks:
            use = this_player_defenses
        latest_hit = sorted(use, key=lambda x : x.get("_time"), reverse=True)
        latest_th = latest_hit[0].get("townhall")
        latest_name = latest_hit[0].get("name")

        num_to_word = {0: "zero", 1 : "one", 2 : "two", 3 : "three"}

        def convert_result(results, result_type):
            rate = defaultdict(lambda: defaultdict(int))
            for result in results:
                townhall = result.get("townhall")
                hr_type = f"{townhall}v{result.get('defender_townhall')}"
                if result.get("clan_name") is not None:
                    clan_to_name[result.get("clan")] = result.get("clan_name")
                if result_type != "defense":
                    by_clan[result.get("clan")]["attacks"] += 1
                    by_clan[result.get("clan")][f"stars"] += result.get("stars")
                    by_clan[result.get("clan")][f"destruction"] += result.get("destruction")
                    by_clan[result.get("clan")][f"{num_to_word.get(result.get('stars'))}_stars"] += 1

                for type in [("All","All"), ("townhall", hr_type), ("freshness", result.get("fresh")),
                             ("clan", result.get("clan")), ("war_type", result.get("war_type")), ("war_size", f"{result.get('war_size')}")]:
                    if result_type == "defense" and type[0] == "clan":
                        continue
                    rate[type]["total_attacks"] += 1
                    rate[type]["total_stars"] += result.get("stars")
                    rate[type]["total_destruction"] += result.get("destruction")
                    rate[type][f"{num_to_word.get(result.get('stars'))}_stars"] += 1
            return rate

        hit_rates = convert_result(this_player_attacks, "attack")
        defense_rates = convert_result(this_player_defenses, "defense")
        player_stats.append({
            "name" : latest_name,
            "tag" : latest_hit[0].get("tag"),
            "townhall" : latest_th,
            "hit_rates" : [dict(stat) | ({"hitrate" : round((stat.get("three_stars", 0) / stat.get("total_attacks")) * 100, 3), "type" : t, "value" : value}
                                         if t != "clan" else {"hitrate" : round((stat.get("three_stars", 0) / stat.get("total_attacks")) * 100, 3), "type" : t, "value" : value, "clan_name" : clan_to_name.get(value)})
                                         for (t, value), stat in hit_rates.items()],
            "defense_rates": [dict(stat) | ({"hitrate" : round((stat.get("three_stars", 0) / stat.get("total_attacks")) * 100, 3), "type" : t, "value" : value}
                                         if t != "clan" else {"hitrate" : round((stat.get("three_stars", 0) / stat.get("total_attacks")) * 100, 3), "type" : t, "value" : value, "clan_name" : clan_to_name.get(value)})
                                         for (t, value), stat in defense_rates.items()],
        })
    totals = {"total_stars" : 0, "total_destruction" : 0, "total_attacks" : 0, "three_stars" : 0, "two_stars" : 0, "one_stars" : 0, "zero_stars" : 0, "average_townhall" : [], "hitrate" : 0.00}
    for data in player_stats:
        first_item = data.get("hit_rates", [])
        if not first_item:
            continue
        first_item = first_item[0]
        totals["total_stars"] += first_item.get("total_stars")
        totals["total_destruction"] += first_item.get("total_destruction")
        totals["total_attacks"] += first_item.get("total_attacks")
        totals["three_stars"] += first_item.get("three_stars", 0)
        totals["two_stars"] += first_item.get("two_stars", 0)
        totals["one_stars"] += first_item.get("one_stars", 0)
        totals["zero_stars"] += first_item.get("zero_stars", 0)
        if data.get("townhall"):
            totals["average_townhall"].append(data.get("townhall"))

    try:
        totals["average_townhall"] = round(mean(totals.get("average_townhall", [0])), 2)
    except:
        totals["average_townhall"] = 0.00
    totals["hitrate"] = round((totals.get("three_stars", 0) / (totals.get("total_attacks") if totals.get("total_attacks") != 0 else 1)) * 100, 3)

    if townhalls:
        townhalls = [int(th) for th in townhalls if th.isnumeric()]
        player_stats = [data for data in player_stats if data.get("townhall") in townhalls]

    if "." in sort_field:
        split_field = sort_field.split(".")
        def sorter(elem):
            try:
                return elem.get(split_field[0], [{}])[0].get(split_field[1], 0)
            except Exception:
                return 0
        new_data = sorted(player_stats, key=sorter, reverse=descending)[:limit]
    else:
        new_data = sorted(player_stats, key=lambda x: x.get(sort_field), reverse=descending)[:limit]

    for count, data in enumerate(new_data, 1):
        data["rank"] = count

    by_clan_totals = []
    for k, v in by_clan.items():
        if clan_to_name.get(k) is None:
            continue
        hitrate = round((v.get("three_stars", 0) / (v.get("attacks", 0) if v.get("total_attacks") != 0 else 1)) * 100, 3)
        by_clan_totals.append({"tag" : k, "name" : clan_to_name.get(k), "hitrate" : hitrate} | dict(v))
    return {"items" : new_data, "totals" : totals, "clan_totals" : by_clan_totals,
            "metadata" : {"sort_order" : ("descending" if descending else "ascending"), "sort_field" : sort_field, "season" : season_or_timestamp}}




@router.get("/capital",
         name="Capital Stats")
@cache(expire=300)
@limiter.limit("10/second")
async def capital_stats(request: Request, response: Response,
                           players: Annotated[List[str], Query(max_length=50)]=None,
                           clans: Annotated[List[str], Query(max_length=25)]=None,
                           server: int =None,
                           sort_field: str = "raided",
                           weekend_or_timestamp: str = None,
                           tied_only: bool = True,
                           descending: bool = True,
                           limit: int = 50):

    limit = min(limit, 500)
    if server:
        clans = await db_client.clans_db.distinct("tag", filter={"server" : server})

    if weekend_or_timestamp is None:
        weekend_or_timestamp = gen_raid_date()

    if not weekend_or_timestamp.isnumeric():
        split_date = weekend_or_timestamp.split("-")
        WEEKEND_START = int(datetime(year=int(split_date[0]), month=int(split_date[1]), day=int(split_date[2]), tzinfo=utc).timestamp())
        print(WEEKEND_START)
        WEEKEND_END = WEEKEND_START + (86400 * 4)
    else:
        WEEKEND_START = int(weekend_or_timestamp)
        WEEKEND_END = int(datetime.now().timestamp())

    def find_fridays_between(start, end):
        total_days: int = (end - start).days + 1
        friday: int = 4
        all_days = [start + timedelta(days=day) for day in range(total_days)]
        return [day for day in all_days if day.weekday() is friday]

    WEEKEND_START = datetime.fromtimestamp(WEEKEND_START, tz=utc)
    WEEKEND_END = datetime.fromtimestamp(WEEKEND_END, tz=utc)
    capital_dates = find_fridays_between(WEEKEND_START, WEEKEND_END)
    WEEKEND_START = WEEKEND_START.strftime('%Y%m%dT%H%M%S.000Z')
    WEEKEND_END = WEEKEND_END.strftime('%Y%m%dT%H%M%S.000Z')

    print(WEEKEND_START)
    print(WEEKEND_END)
    clan_to_name = {}
    by_clan = defaultdict(lambda : defaultdict(int))

    if not players:
        basic_clans = await db_client.basic_clan.find({"tag": {"$in" : clans}}).to_list(length=None)
        players = []
        for b_c in basic_clans:
            clan_to_name[b_c.get("tag")] = b_c.get("name")
            if not tied_only:
                players += [m.get("tag") for m in b_c.get("memberList", [])]

    stats = defaultdict(lambda : defaultdict(int))
    if players:
        pipeline = [
            {"$match" : {"$and" : [{"data.members.tag" : {"$in" : players}}, {"data.startTime" : {"$gte" : WEEKEND_START}}, {"data.endTime" : {"$lte" : WEEKEND_END}}]}},
            {"$unset": ["_id"]}
        ]
        raids = await db_client.capital.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

        player_stats = await db_client.player_stats_db.find({"tag" : {"$in" : players}}, {"tag" : 1, "capital_gold" : 1}).to_list(length=None)
        donated_capital = {}
        for p in player_stats:
            for date in capital_dates:
                stats[p.get("tag")]["donated"] += sum(p.get("capital_gold", {}).get(str(date.date()), {}).get("donate", [0]))
            donated_capital[p.get("tag")] = p.get("capital_gold", {})
        for raid in raids:
            clan_tag = raid.get("clan_tag")
            raid = raid.get("data")
            raid = coc.RaidLogEntry(data=raid, client=coc_client)
            raid_date = str(raid.start_time.time.date())
            for tag in players:
                raid_member = raid.get_member(tag)
                stats[tag]["name"] = raid_member.name
                stats[tag]["tag"] = raid_member.tag
                stats[tag]["raided"] += raid_member.capital_resources_looted
                stats[tag]["attacks"] += raid_member.attack_count
                stats[tag]["donated"] += sum(donated_capital.get(tag, {}).get(raid_date, {}).get("donate", [0]))

                by_clan[clan_tag]["raided"] += raid_member.capital_resources_looted
                by_clan[clan_tag]["donated"] += sum(donated_capital.get(tag, {}).get(raid_date, {}).get("donate", [0]))
                by_clan[clan_tag]["attacks"] += raid_member.attack_count

    elif clans:
        pipeline = [
            {"$match": {"$and": [{"clan_tag": {"$in": clans}}, {"data.startTime": {"$gte": WEEKEND_START}}, {"data.endTime": {"$lte": WEEKEND_END}}]}},
            {"$unset": ["_id"]}
        ]
        raids = await db_client.capital.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

        player_tags = set()
        for raid in raids:
            raid = raid.get("data")
            raid = coc.RaidLogEntry(data=raid, client=coc_client)
            for raid_member in raid.members:
                player_tags.add(raid_member.tag)

        player_stats = await db_client.player_stats_db.find({"tag": {"$in": list(player_tags)}}, {"tag": 1, "capital_gold": 1}).to_list(length=None)
        donated_capital = {}
        for p in player_stats:
            for date in capital_dates:
                stats[p.get("tag")]["donated"] += sum(p.get("capital_gold", {}).get(str(date.date()), {}).get("donate", [0]))
            donated_capital[p.get("tag")] = p.get("capital_gold", {})
        for raid in raids:
            clan_tag = raid.get("clan_tag")
            raid = raid.get("data")
            raid = coc.RaidLogEntry(data=raid, client=coc_client)
            raid_date = str(raid.start_time.time.date())
            for raid_member in raid.members:
                tag = raid_member.tag
                stats[tag]["name"] = raid_member.name
                stats[tag]["tag"] = raid_member.tag
                stats[tag]["raided"] += raid_member.capital_resources_looted
                stats[tag]["attacks"] += raid_member.attack_count
                stats[tag]["donated"] += sum(donated_capital.get(tag, {}).get(raid_date, {}).get("donate", [0]))
                stats[tag]["medals"] += (raid.offensive_reward * raid_member.attack_count) + raid.defensive_reward
                by_clan[clan_tag]["raided"] += raid_member.capital_resources_looted
                by_clan[clan_tag]["donated"] += sum(donated_capital.get(tag, {}).get(raid_date, {}).get("donate", [0]))
                by_clan[clan_tag]["attacks"] += raid_member.attack_count
            by_clan[clan_tag]["medals"] += raid.offensive_reward * 6 + raid.defensive_reward

    totals = {"total_donated" : 0, "total_raided" : 0, "total_attacks" : 0, "total_medals" : 0}
    for data in stats.values():
        totals["total_donated"] += data.get("donated")
        totals["total_raided"] += data.get("raided")
        totals["total_attacks"] += data.get("attacks")
        totals["total_medals"] += data.get("medals")

    stats = list(stats.values())
    new_data = sorted(stats, key=lambda x: x.get(sort_field), reverse=descending)[:limit]

    for count, data in enumerate(new_data, 1):
        data["rank"] = count

    if not clan_to_name:
        basic_clans = await db_client.basic_clan.find({"tag": {"$in" : list(by_clan.keys())}}).to_list(length=None)
        for b_c in basic_clans:
            clan_to_name[b_c.get("tag")] = b_c.get("name")

    by_clan_totals = []
    for k, v in by_clan.items():
        if clan_to_name.get(k) is None:
            continue
        by_clan_totals.append({"tag" : k, "name" : clan_to_name.get(k)} | dict(v))


    return {"items" : new_data, "totals" : totals, "clan_totals" : by_clan_totals,
            "metadata" : {"sort_order" : ("descending" if descending else "ascending"), "sort_field" : sort_field, "weekend" : weekend_or_timestamp}}







