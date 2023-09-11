import os
import re
import aiohttp
import asyncio
import pytz
import motor.motor_asyncio
import uvicorn
import io
import pandas as pd
import coc
import ujson

from coc.ext import discordlinks
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Query, HTTPException
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from Models.models import *
from fastapi.openapi.utils import get_openapi
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from typing import List, Union
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from collections import defaultdict
from helper import IMAGE_CACHE, download_image
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from bs4 import BeautifulSoup
from redis import asyncio as aioredis
from routers import leagues, player, capital, other
from bson.objectid import ObjectId

load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        # you probably want some kind of logging here
        return Response("Not Found", status_code=404)

app.middleware('http')(catch_exceptions_middleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(player.router)
app.include_router(capital.router)
app.include_router(leagues.router)
app.include_router(other.router)

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

link_client = None
CACHED_SEASONS = []

def fix_tag(tag:str):
    tag = tag.replace('%23', '')
    tag = "#" + re.sub(r"[^A-Z0-9]+", "", tag.upper()).replace("O", "0")
    return tag

@app.on_event("startup")
async def startup_event():
    global link_client
    link_client = coc.ext.discordlinks.DiscordLinkClient = await discordlinks.login(os.getenv("LINK_API_USER"), os.getenv("LINK_API_PW"))
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


@app.get("/", include_in_schema=False,
         response_class=RedirectResponse)
async def docs():
    return f"https://api.clashking.xyz/docs"



#CLAN ENDPOINTS
@app.get("/clan/{clan_tag}/stats",
         tags=["Clan Endpoints"],
         name="All stats for a clan (activity, donations, etc)")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_historical(clan_tag: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    result = await clan_stats.find_one({"tag": clan_tag})
    if result is not None:
        del result["_id"]
    return result

@app.get("/clan/{clan_tag}/basic",
         tags=["Clan Endpoints"],
         name="Basic Clan Object")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_basic(clan_tag: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    result = await basic_clan.find_one({"tag": clan_tag})
    if result is not None:
        del result["_id"]
    return result


@app.get("/clan/{clan_tag}/historical/{season}",
         tags=["Clan Endpoints"],
         name="Historical data for clan events")
@cache(expire=300)
@limiter.limit("5/second")
async def clan_historical(clan_tag: str, season: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))
    historical_data = await clan_history.find({"$and": [{"tag": fix_tag(clan_tag)},
                                                          {"time": {"$gte": season_start.timestamp()}},
                                                          {"time": {"$lte": season_end.timestamp()}}]}).sort("time", 1).to_list(length=None)
    breakdown = defaultdict(list)
    for data in historical_data:
        del data["_id"]
        breakdown[data["type"]].append(data)

    result = {}
    for key, item in breakdown.items():
        result[key] = item
    return dict(result)


@app.get("/clan/{clan_tag}/join-leave/{season}",
         tags=["Clan Endpoints"],
         name="Join Leaves in a season")
@cache(expire=300)
@limiter.limit("5/second")
async def clan_join_leave(clan_tag: str, season: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))
    result = await clan_join_leave.find({"$and": [{"tag": clan_tag},
                                                          {"time": {"$gte": season_start.timestamp()}},
                                                          {"time": {"$lte": season_end.timestamp()}}]}).sort("time", 1).to_list(length=None)
    if result:
        for r in result:
            del r["_id"]
    return dict(result)


@app.get("/clan/{clan_tag}/cache",
         tags=["Clan Endpoints"],
         name="Cached endpoint response")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_cache(clan_tag: str, request: Request, response: Response):
    cache_data = await clan_cache_db.find_one({"tag": fix_tag(clan_tag)})
    if not cache_data:
        return {"No Clan Found": clan_tag}
    del cache_data["data"]["_response_retry"]
    return cache_data["data"]


@app.post("/clan/bulk",
         tags=["Clan Endpoints"],
         name="Cached endpoint response (bulk fetch)")
@limiter.limit("5/second")
async def bulk_clan_cache(clan_tags: List[str], request: Request, response: Response):
    cache_data = await clan_cache_db.find({"tag": {"$in": [fix_tag(tag) for tag in clan_tags]}}).to_list(length=500)
    modified_result = []
    for data in cache_data:
        del data["data"]["_response_retry"]
        modified_result.append(data["data"])
    return modified_result


@app.get("/clan/search",
         tags=["Clan Endpoints"],
         name="Search Clans by Filtering")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_filter(request: Request, response: Response,  limit: int= 100, location_id: int = None, minMembers: int = None, maxMembers: int = None,
                      minLevel: int = None, maxLevel: int = None, openType: str = None,
                          minWarWinStreak: int = None, minWarWins: int = None, minClanTrophies: int = None, maxClanTrophies: int = None, capitalLeague: str= None,
                          warLeague: str= None, memberList: bool = True, townhallData: bool = False, before:str =None, after: str=None):
    queries = {}
    queries['$and'] = []
    if location_id:
        queries['$and'].append({'location.id': location_id})

    if minMembers:
        queries['$and'].append({"members": {"$gte" : minMembers}})

    if maxMembers:
        queries['$and'].append({"members": {"$lte" : maxMembers}})

    if minLevel:
        queries['$and'].append({"level": {"$gte" : minLevel}})

    if maxLevel:
        queries['$and'].append({"level": {"$lte" : maxLevel}})

    if openType:
        queries['$and'].append({"type": openType})

    if capitalLeague:
        queries['$and'].append({"capitalLeague": capitalLeague})

    if warLeague:
        queries['$and'].append({"warLeague": warLeague})

    if minWarWinStreak:
        queries['$and'].append({"warWinStreak": {"$gte": minWarWinStreak}})

    if minWarWins:
        queries['$and'].append({"warWins": {"$gte": minWarWins}})

    if minClanTrophies:
        queries['$and'].append({"clanPoints": {"$gte": minClanTrophies}})

    if maxClanTrophies:
        queries['$and'].append({"clanPoints": {"$gte": maxClanTrophies}})

    if after:
        queries['$and'].append({"_id": {"$gt": ObjectId(after)}})

    if before:
        queries['$and'].append({"_id": {"$lt": ObjectId(before)}})


    if queries["$and"] == []:
        queries = {}

    limit = min(limit, 1000)
    results = await basic_clan.find(queries).limit(limit).sort("_id", 1).to_list(length=limit)
    return_data = {"items" : [], "before": "", "after" : ""}
    if results:
        if townhallData and memberList:
            member_tags = []
            for clan in results:
                for member in clan.get("memberList"):
                    member_tags.append(member.get("tag"))
            pipeline = [{"$match" : {"tag" : {"$in" : member_tags}}},
                        {"$group" : {"_id" : "$tag", "th" : {"$last" : "$townhall"}}}]
            th_results = await attack_db.aggregate(pipeline).to_list(length=None)
            th_results = {item.get("_id") : item.get("th") for item in th_results}

        return_data["before"] = str(results[0].get("_id"))
        return_data["after"] = str(results[-1].get("_id"))
        for data in results:
            del data["_id"]
            if not memberList:
                del data["memberList"]
            else:
                for member in data["memberList"]:
                    tag = member.get("tag")
                    member["townHallLevel"] = th_results.get(tag, None)
        return_data["items"] = results
    return Response(content=ujson.dumps(return_data), media_type="application/json")



#WAR STATS
@app.get("/war/{clan_tag}/log",
         tags=["War Endpoints"],
         name="Warlog for a clan, filled in with data where possible")
@cache(expire=300)
@limiter.limit("30/second")
async def war_log(clan_tag: str, request: Request, response: Response, limit: int= 50):
    clan_tag = fix_tag(clan_tag)
    clan_results = await war_logs_db.find({"clan.tag" : clan_tag}).to_list(length=None)
    opponent_results = await war_logs_db.find({"opponent.tag" : clan_tag}).to_list(length=None)

    data_ids = list(set([result["endTime"] for result in clan_results] + [result["endTime"] for result in opponent_results]))
    full_wars = await clan_wars.find({"$and" : [{"$or" : [{"data.clan.tag" : clan_tag}, {"data.opponent.tag" : clan_tag}]},{"data.endTime" : {"$in" : data_ids}}]}).to_list(length=None)
    wars_by_endtime = {}
    for war in full_wars:
        try:
            del war["data"]["_response_retry"]
        except:
            pass
        wars_by_endtime[war["data"]["endTime"]] = war["data"]

    times_alr_found = set()
    actual_results = []
    for result in clan_results:
        del result["_id"]
        if wars_by_endtime.get(result["endTime"]) is not None:
            result["data"] = wars_by_endtime.get(result["endTime"])
        actual_results.append(result)
        times_alr_found.add(result["timeStamp"])

    for result in opponent_results:
        if result["timeStamp"] not in times_alr_found:
            del result["_id"]
            if result["result"] == "win":
                result["result"] = "lose"
            elif result["result"] == "lose":
                result["result"] = "win"
            old_opponent = result["opponent"]
            result["opponent"] = result["clan"]
            result["clan"] = old_opponent
            result["clan"]["attacks"] = 0
            result["clan"]["expEarned"] = 0
            if wars_by_endtime.get(result["endTime"]) is not None:
                result["data"] = wars_by_endtime.get(result["endTime"])
            actual_results.append(result)

    actual_results = sorted(actual_results, key=lambda x: x["timeStamp"], reverse=True)
    return actual_results[:limit]


@app.get("/war/{clan_tag}/previous",
         tags=["War Endpoints"],
         name="Previous Wars for a clan")
@cache(expire=300)
@limiter.limit("30/second")
async def war_previous(clan_tag: str, request: Request, response: Response, limit: int= 50):
    clan_tag = fix_tag(clan_tag)
    full_wars = await clan_wars.find({"$and" : [{"$or" : [{"data.clan.tag" : clan_tag}, {"data.opponent.tag" : clan_tag}]}]}).to_list(length=None)
    found_ids = set()
    new_wars = []
    for war in full_wars:
        id = war.get("data").get("preparationStartTime")
        if id in found_ids:
            continue
        try:
            del war["_response_retry"]
        except:
            pass
        new_wars.append(war.get("data"))
        found_ids.add(id)

    actual_results = sorted(new_wars, key=lambda x: x.get("endTime", 0), reverse=True)
    return actual_results[:limit]


@app.get("/war/{clan_tag}/basic",
         tags=["War Endpoints"],
         name="Basic War Info, Bypasses Private War Log if Possible")
@cache(expire=300)
@limiter.limit("30/second")
async def basic_war_info(clan_tag: str, request: Request, response: Response):
    now = datetime.utcnow().timestamp() - 183600
    result = await clan_wars.find_one({"$and" : [{"clan" : fix_tag(clan_tag)}, {"custom_id": None}, {"endTime" : {"$gte" : now}}]})
    if result is None:
        result = await clan_wars.find_one({"$and" : [{"opponent" : fix_tag(clan_tag)}, {"custom_id" : None}, {"endTime" : {"$gte" : now}}]})
    if result is not None:
        del result["_id"]
    return result


#REDIRECT
@app.get("/p/{player_tag}",
         response_class=RedirectResponse,
         tags=["Redirect"],
         name="Shortform Player Profile URL",
         include_in_schema=False)
async def redirect_fastapi(player_tag: str):
    return f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23{player_tag}"


@app.get("/player",
         tags=["Redirect"],
         name="Player Link URL",
         include_in_schema=False)
async def redirect_fastapi_player(tag: str):
    tag = tag.split("=")[-1]
    tag = "#" + tag
    headers = {"Accept": "application/json", "authorization": f"Bearer {os.getenv('COC_KEY')}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"https://cocproxy.royaleapi.dev/v1/players/{tag.replace('#', '%23')}",
                headers=headers) as response:
            item = await response.json()
    name = item.get("name")
    trophies = item.get("trophies")
    league_icon = item.get("league", {}).get("iconUrls", {}).get("small", "https://clashking.b-cdn.net/unranked.png")
    league = item.get("league", {}).get("name", "Unranked League")
    war_stars = item.get("warStars")
    townhall = item.get("townHallLevel")
    donations = item.get("donations")
    received = item.get("donationsReceived")

    HTMLFile = open("test.html", "r")
    # Reading the file
    index = HTMLFile.read()
    soup = BeautifulSoup(index)


    metatag = soup.new_tag('meta')
    metatag.attrs["property"] = 'og:title'
    metatag.attrs['content'] = f"{name} | Townhall {townhall}"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["property"] = 'og:description'
    metatag.attrs['content'] = f"•{trophies} trophies, {league}\n" \
                               f"•Donations: ▲{donations} ▼{received}\n" \
                               f"•⭐{war_stars} War Stars\n"
    soup.head.append(metatag)


    metatag = soup.new_tag('meta')
    metatag.attrs["name"] = 'description'
    metatag.attrs['content'] = f"•{trophies} trophies, {league}\n" \
                               f"•Donations: ▲{donations} ▼{received}\n" \
                               f"•⭐{war_stars} War Stars\n"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["property"] = 'og:image'
    metatag.attrs['content'] = league_icon
    soup.head.append(metatag)

    with open("output1.html", "w", encoding='utf-8') as file:
        file.write(str(soup))

    HTMLFile = open("output1.html", "r")
    return HTMLResponse(content=HTMLFile.read(), status_code=200)



@app.get("/c/{clan_tag}",
         response_class=RedirectResponse,
         tags=["Redirect"],
         name="Shortform Clan Profile URL",
         include_in_schema=False)
async def redirect_fastapi_clan(clan_tag: str):
    return f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{clan_tag}"


@app.get("/base",
         response_class=RedirectResponse,
         tags=["Redirect"],
         name="Base Link URL",
         include_in_schema=False)
async def redirect_fastapi_base(id: str):
    id = id.split("=")[-1]
    base_id = id.replace(":", "%3A")
    base = await base_stats.find_one({"base_id": base_id})
    if base is not None:
        await base_stats.update_one({"base_id": base_id}, {"$inc": {"downloads": 1},
                                                           "$set": {"unix_time": int(datetime.now().timestamp()),
                                                                    "time": datetime.today().replace(microsecond=0)}},
                                upsert=True)
    base = await base_stats.find_one({"base_id" : base_id})
    HTMLFile = open("test.html", "r")
    # Reading the file
    index = HTMLFile.read()
    soup = BeautifulSoup(index)

    metatag = soup.new_tag('meta')
    metatag.attrs["property"] = 'og:title'
    metatag.attrs['content'] = f"Townhall {base.get('townhall')} Base by {base.get('builder')}"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["property"] = 'og:description'
    type_ = ''.join(base.get("type"))
    metatag.attrs['content'] = f"{base.get('downloads')} downloads | Tags: {type_}"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["name"] = 'description'
    metatag.attrs['content'] = f"{base.get('downloads')} downloads | Tags: {type_}"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["property"] = 'og:image'
    metatag.attrs['content'] = f"https://cdn.clashking.xyz/{base.get('pic_id')}.png"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["name"] = 'twitter:card'
    metatag.attrs['content'] = f"summary_large_image"
    soup.head.append(metatag)

    metatag = soup.new_tag('meta')
    metatag.attrs["name"] = 'twitter:image'
    metatag.attrs['content'] = f"https://cdn.clashking.xyz/{base.get('pic_id')}.png"
    soup.head.append(metatag)

    with open("output1.html", "w", encoding='utf-8') as file:
        file.write(str(soup))

    HTMLFile = open("output1.html", "r")
    return HTMLResponse(content=HTMLFile.read(), status_code=200)


#Ranking History
@app.get("/ranking/player-trophies/{location}/{date}",
         tags=["Leaderboard History"],
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def player_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await player_trophies.find_one({"$and" : [{"location" : location}, {"date" : date}]})
    return r.get("data")

@app.get("/ranking/player-builder/{location}/{date}",
         tags=["Leaderboard History"],
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def player_builder_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await player_versus_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")

@app.get("/ranking/clan-trophies/{location}/{date}",
         tags=["Leaderboard History"],
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await clan_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@app.get("/ranking/clan-builder/{location}/{date}",
         tags=["Leaderboard History"],
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_builder_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await clan_versus_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")

@app.get("/ranking/clan-capital/{location}/{date}",
         tags=["Leaderboard History"],
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_capital_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await capital_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")



#GAME DATA
@app.get("/assets",
         tags=["Game Data"],
         name="Link to download a zip with all assets")
@limiter.limit("5/second")
async def assets(request: Request, response: Response):
    return {"download-link" : "https://cdn.clashking.xyz/Out-Sprites.zip"}

@app.get("/csv",
         tags=["Game Data"],
         name="Download zip of all csv files")
@limiter.limit("5/second")
async def csv(request: Request, response: Response):
    file_name = "compressed-csv.zip"
    file_path = os.getcwd() + "/" + file_name
    return FileResponse(path=file_path, media_type='application/octet-stream', filename="gamefile-csv.zip")

@app.get("/json/{type}",
         tags=["Game Data"],
         name="View json game data (/json/list, for list of types)")
@limiter.limit("5/second")
async def json(type: str, request: Request, response: Response):
    if type == "list":
        return {"files" : ["troops", "heroes", "spells", "buildings", "pets", "supers", "townhalls", "translations"]}
    file_name = f"game-json/{type}.json"
    file_path = os.getcwd() + "/" + file_name
    with open(file_path) as json_file:
        data = ujson.load(json_file)
        return data

@app.get("/goldpass",
         tags=["Game Data"],
         name="Gold Pass Item Info")
@limiter.limit("30/second")
async def gold_pass(season: str, request: Request, response: Response):
    return {"type" : "Work In Progress"}

#UTILS
@app.post("/table",
         tags=["Utils"],
         name="Custom Table",
         include_in_schema=False)
@limiter.limit("5/second")
async def table_render(info: Dict, request: Request, response: Response):
    columns = info.get("columns")
    positions = info.get("positions")
    data = info.get("data")
    logo = info.get("logo")
    badge_columns = info.get("badge_columns")
    title = info.get("title")

    fig = plt.figure(figsize=(8, 10), dpi=300)
    img = plt.imread("clouds.jpg")
    ax = plt.subplot()

    df_final = pd.DataFrame(data, columns=columns)
    ncols = len(columns) + 1
    nrows = df_final.shape[0]

    ax.set_xlim(0, ncols + 1)
    ax.set_ylim(0, nrows + 1)

    positions = [0.15, 3.5, 4.5, 5.5, 6.5, 7.5][:len(columns)]

    # -- Add table's main text
    for i in range(nrows):
        for j, column in enumerate(columns):
            if j == 0:
                ha = 'left'
            else:
                ha = 'center'
            if column == 'Min':
                continue
            else:
                text_label = f'{df_final[column].iloc[i]}'
                weight = 'normal'
            ax.annotate(
                xy=(positions[j], i + .5),
                text=text_label,
                ha=ha,
                va='center',
                weight=weight
            )

    # -- Transformation functions
    DC_to_FC = ax.transData.transform
    FC_to_NFC = fig.transFigure.inverted().transform
    # -- Take data coordinates and transform them to normalized figure coordinates
    DC_to_NFC = lambda x: FC_to_NFC(DC_to_FC(x))
    # -- Add nation axes
    ax_point_1 = DC_to_NFC([2.25, 0.25])
    ax_point_2 = DC_to_NFC([2.75, 0.75])
    ax_width = abs(ax_point_1[0] - ax_point_2[0])
    ax_height = abs(ax_point_1[1] - ax_point_2[1])

    for x in range(0, nrows):
        ax_coords = DC_to_NFC([2.25, x + .25])
        flag_ax = fig.add_axes(
            [ax_coords[0], ax_coords[1], ax_width, ax_height]
        )

        badge = await download_image(badge_columns[x])
        flag_ax.imshow(Image.open(badge))
        flag_ax.axis('off')

    ax_point_1 = DC_to_NFC([4, 0.05])
    ax_point_2 = DC_to_NFC([5, 0.95])
    ax_width = abs(ax_point_1[0] - ax_point_2[0])
    ax_height = abs(ax_point_1[1] - ax_point_2[1])

    # -- Add column names
    column_names = columns
    for index, c in enumerate(column_names):
        if index == 0:
            ha = 'left'
        else:
            ha = 'center'
        ax.annotate(
            xy=(positions[index], nrows + .25),
            text=column_names[index],
            ha=ha,
            va='bottom',
            weight='bold'
        )

    # Add dividing lines
    ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [nrows, nrows], lw=1.5, color='black', marker='', zorder=4)
    ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [0, 0], lw=1.5, color='black', marker='', zorder=4)
    for x in range(1, nrows):
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [x, x], lw=1.15, color='gray', ls=':', zorder=3, marker='')

    ax.fill_between(
        x=[0, 2],
        y1=nrows,
        y2=0,
        color='lightgrey',
        alpha=0.5,
        ec='None'
    )

    ax.set_axis_off()

    # -- Final details
    logo_ax = fig.add_axes(
        [0.825, 0.89, .05, .05]
    )
    club_icon = await download_image(logo)
    logo_ax.imshow(Image.open(club_icon))
    logo_ax.axis('off')
    fig.text(
        x=0.15, y=.90,
        s=title,
        ha='left',
        va='bottom',
        weight='bold',
        size=12
    )
    temp = io.BytesIO()
    # plt.imshow(img,  aspect="auto")
    background_ax = plt.axes([.10, .08, .85, .87])  # create a dummy subplot for the background
    background_ax.set_zorder(-1)  # set the background subplot behind the others
    background_ax.axis("off")
    background_ax.imshow(img, aspect='auto')  # show the backgroud image
    fig.savefig(
        temp,
        dpi=200,
        transparent=True,
        bbox_inches='tight'
    )
    plt.close(fig)
    temp.seek(0)
    await upload_to_cdn(picture=temp, title=title)
    title = title.replace(" ", "_").lower()
    return {"link" : f"https://cdn.clashking.xyz/{title}.png"}


@app.get("/guild_links/{guild_id}",
         tags=["Utils"],
         name="Get clans that are linked to a discord guild",
         include_in_schema=False)
@cache(expire=300)
@limiter.limit("30/second")
async def guild_links(guild_id: int, request: Request, response: Response):
    return {}

@app.get("/player_tags",
         tags=["Utils"],
         name="Get a list of all player tags in database")
@cache(expire=3600)
@limiter.limit("1/minute")
async def player_tags(request: Request, response: Response):
    tags = await player_stats_db.distinct("tag")
    return {"tags" : tags}


@app.get("/permalink/{clanTag}",
         tags=["Utils"],
         name="Permanent Link to Clan Badge URL")
async def permalink(clan_tag: str):
    headers = {"Accept": "application/json", "authorization": f"Bearer {os.getenv('COC_KEY')}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"https://cocproxy.royaleapi.dev/v1/clans/{clan_tag.replace('#', '%23')}",
                headers=headers) as response:
            items = await response.json()
    image_link = items["badgeUrls"]["large"]

    async def fetch(url, session):
        async with session.get(url) as response:
            image_data = await response.read()
            return image_data

    tasks = []
    async with aiohttp.ClientSession() as session:
        tasks.append(fetch(image_link, session))
        responses = await asyncio.gather(*tasks)
        await session.close()
    image_bytes: bytes = responses[0]
    return Response(content=image_bytes, media_type="image/png")


@app.get("/renderhtml",
         tags=["Utils"],
         name="Render links to HTML as a page",
         include_in_schema=False)
async def render(url: str):
    async def fetch(u, session):
        async with session.get(u) as response:
            image_data = await response.read()
            return image_data

    async with aiohttp.ClientSession() as session:
        response = await fetch(str(url), session)
        await session.close()
    return HTMLResponse(content=response, status_code=200)

@app.post("/discord_links",
         tags=["Utils"],
         name="Get discord links for tags",
         include_in_schema=False)
@limiter.limit("5/second")
async def discord_link(player_tags: List[str], request: Request, response: Response):
    global link_client
    result = await link_client.get_links(*player_tags)
    return dict(result)


@app.get("/v1/{url:path}",
         tags=["Utils"],
         name="Test a coc api endpoint, very high ratelimit, only for testing without auth",
         include_in_schema=False)
@cache(expire=60)
@limiter.limit("30/minute")
async def test_endpoint(url: str, request: Request, response: Response):
    url = url.replace("#", '%23')
    url = url.replace("!", '%23')
    url = url.split("?")[0]
    headers = {"Accept": "application/json", "authorization": f"Bearer {os.getenv('COC_KEY')}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"https://cocproxy.royaleapi.dev/v1/{url}?limit=200", headers=headers) as response:
            item = await response.json()
    return item

async def upload_to_cdn(picture, title: str):
    headers = {
        "content-type": "application/octet-stream",
        "AccessKey": os.getenv("BUNNY_ACCESS_KEY")
    }
    payload = picture.read()
    title = title.replace(" ", "_").lower()
    async with aiohttp.ClientSession() as session:
        async with session.put(url=f"https://ny.storage.bunnycdn.com/clashking/{title}.png", headers=headers, data=payload) as response:
            await session.close()


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
    uvicorn.run("main:app", host='0.0.0.0', port=443, ssl_keyfile="/etc/letsencrypt/live/api.clashking.xyz/privkey.pem", ssl_certfile="/etc/letsencrypt/live/api.clashking.xyz/fullchain.pem", workers=6)
    #uvicorn.run("main:app", host='localhost', port=80)
