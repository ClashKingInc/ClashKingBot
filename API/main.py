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
from fastapi.responses import HTMLResponse
from collections import defaultdict
from helper import IMAGE_CACHE, download_image

utc = pytz.utc
load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))

looper = client.looper
new_looper = client.new_looper

war_logs_db = looper.war_logs
player_stats_db = new_looper.player_stats
attack_db = looper.warhits
player_leaderboard_db = new_looper.leaderboard_db
player_history = new_looper.player_history
player_cache_db = new_looper.player_cache
clan_cache_db = new_looper.clan_cache
clan_wars = looper.clan_wars
legend_history = client.looper.legend_history
base_stats = looper.base_stats

ranking_history = client.ranking_history
player_trophies = ranking_history.player_trophies
player_versus_trophies = ranking_history.player_versus_trophies
clan_trophies = ranking_history.clan_trophies
clan_versus_trophies = ranking_history.clan_versus_trophies
capital = ranking_history.capital

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


@app.get("/",
         response_class=RedirectResponse)
async def docs():
    return f"https://api.clashking.xyz/docs"


@app.get("/player/{player_tag}/stats",
         response_model=Player,
         tags=["Player Endpoints"],
         name="Overview of stats for a player")
@limiter.limit("10/second")
async def player_stat(player_tag: str, request: Request, response: Response):
    player_tag = player_tag and "#" + re.sub(r"[^A-Z0-9]+", "", player_tag.upper()).replace("O", "0")
    result = await player_stats_db.find_one({"tag": player_tag})
    lb_spot = await player_leaderboard_db.find_one({"tag": player_tag})
    war_hits = await attack_db.find({"tag": player_tag}).to_list(length=250)
    historical_data = await player_history.find({"tag": player_tag}).sort("time", 1).to_list(length=25000)

    if result is None:
        raise HTTPException(status_code=404, detail=f"No player found")
    del result["_id"]
    try:
        del result["legends"]["streak"]
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
    hits = []
    for hit in war_hits:
        del hit["_id"]
        hits.append(hit)
    result["war_hits"] = hits

    breakdown = defaultdict(list)
    for data in historical_data:
        del data["_id"]
        breakdown[data["type"]].append(data)

    result["historical_data"] = {}
    for key, item in breakdown.items():
        result["historical_data"][key] = item

    return dict(result)


@app.get("/player/{player_tag}/legends",
         tags=["Player Endpoints"],
         name="Legend stats for a player")
@limiter.limit("10/second")
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


@app.get("/player/{player_tag}/historical",
         tags=["Player Endpoints"],
         name="Historical data for player events")
@limiter.limit("10/second")
async def player_historical(player_tag: str, request: Request, response: Response):
    return {}

@app.get("/player/{player_tag}/legend_rankings",
         tags=["Player Endpoints"],
         name="Previous player legend rankings")
@limiter.limit("10/second")
async def player_legend_rankings(player_tag: str, request: Request, response: Response, limit:int = 10):

    player_tag = fix_tag(player_tag)
    results = await legend_history.find({"tag": player_tag}).sort("season", -1).limit(limit).to_list(length=None)
    for result in results:
        del result["_id"]

    return results

@app.get("/player/{player_tag}/cache",
         tags=["Player Endpoints"],
         name="Cached endpoint response")
@limiter.limit("10/second")
async def player_cache(player_tag: str, request: Request, response: Response):
    cache_data = await player_cache_db.find_one({"tag": fix_tag(player_tag)})
    if not cache_data:
        return {"No Player Found" : player_tag}
    return cache_data["data"]

@app.post("/player/bulk",
          tags=["Player Endpoints"],
          name="Cached endpoint response (bulk fetch)")
@limiter.limit("10/second")
async def player_bulk(player_tags: List[str], request: Request, resonse: Response):
    cache_data = await player_cache_db.find({"tag": {"$in": [fix_tag(tag) for tag in player_tags]}}).to_list(length=500)
    modified_result = []
    for data in cache_data:
        del data["_id"]
        modified_result.append(data["data"])
    return modified_result


#CLAN CAPITAL ENDPOINTS
@app.get("/capital/{clan_tag}",
         tags=["Clan Capital Endpoints"],
         name="Log of Raid Weekends")
@limiter.limit("10/second")
async def capital_log(clan_tag: str, request: Request, response: Response):
    return {}

@app.post("/capital/bulk",
         tags=["Clan Capital Endpoints"],
         name="Fetch Raid Weekends in Bulk")
@limiter.limit("10/second")
async def capital(clan_tags: List[str], request: Request, response: Response):
    return {}

#CLAN ENDPOINTS
@app.get("/clan/{clan_tag}/historical",
         tags=["Clan Endpoints"],
         name="Historical data for clan events")
@limiter.limit("10/second")
async def clan_historical(clan_tag: str, request: Request, response: Response):
    return {}

@app.get("/clan/{clan_tag}/cache",
         tags=["Clan Endpoints"],
         name="Cached endpoint response")
@limiter.limit("10/second")
async def clan_cache(clan_tag: str, request: Request, response: Response):
    cache_data = await clan_cache_db.find_one({"tag": fix_tag(clan_tag)})
    if not cache_data:
        return {"No Clan Found": clan_tag}
    del cache_data["data"]["_response_retry"]
    return cache_data["data"]

@app.post("/clan/bulk-cache",
         tags=["Clan Endpoints"],
         name="Cached endpoint response (bulk fetch)")
@limiter.limit("10/second")
async def bulk_clan_cache(clan_tags: List[str], request: Request, response: Response):
    cache_data = await clan_cache_db.find({"tag": {"$in": [fix_tag(tag) for tag in clan_tags]}}).to_list(length=500)
    modified_result = []
    for data in cache_data:
        del data["data"]["_response_retry"]
        modified_result.append(data["data"])
    return modified_result


#WAR STATS
@app.get("/war/{clan_tag}/log",
         tags=["War Endpoints"],
         name="Warlog for a clan, filled in with data where possible")
@limiter.limit("10/second")
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


#REDIRECT
@app.get("/p/{player_tag}",
         response_class=RedirectResponse,
         tags=["Redirect"],
         name="Shortform Player Profile URL")
async def redirect_fastapi(player_tag: str):
    return f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23{player_tag}"


@app.get("/c/{clan_tag}",
         response_class=RedirectResponse,
         tags=["Redirect"],
         name="Shortform Clan Profile URL")
async def redirect_fastapi_clan(clan_tag: str):
    return f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{clan_tag}"


@app.get("/base",
         response_class=RedirectResponse,
         tags=["Redirect"],
         name="Base Link URL")
async def redirect_fastapi_base(id: str):
    id = id.split("=")[-1]
    base_id = id.replace(":", "%3A")
    await base_stats.update_one({"base_id": base_id}, {"$inc": {"downloads": 1},
                                                       "$set": {"unix_time": int(datetime.now().timestamp()),
                                                                "time": datetime.today().replace(microsecond=0)}},
                                upsert=True)
    HTMLFile = open("test.html", "r")

    # Reading the file
    index = HTMLFile.read()
    return HTMLResponse(content=index, status_code=200)


#SEARCH ENDPOINTS
@app.get("/search-clan/{name}",
         tags=["Search"],
         name="Search for clans by name")
@limiter.limit("10/second")
async def search_clans(name: str, request: Request, response: Response):
    return {}

@app.get("/search-player/{name}",
         tags=["Search"],
         name="Search for players by name")
@limiter.limit("10/second")
async def search_players(player: str, request: Request, response: Response):
    return {}

#Ranking History
@app.get("/player_trophies/{location}/{date}",
         tags=["Leaderboard History"],
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@limiter.limit("10/second")
async def player_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await player_trophies.find_one({"$and" : [{"location" : location}, {"date" : date}]})
    return r.get("data")

#UTILS
@app.post("/table",
         tags=["Utils"],
         name="Custom Table")
@limiter.limit("10/second")
async def table_render(info: Dict, request: Request, response: Response):
    columns = info.get("columns")
    positions = info.get("positions")
    data = info.get("data")
    logo = info.get("logo")
    badge_columns = info.get("badge_columns")
    title = info.get("title")

    image_bytes = IMAGE_CACHE.get(title)
    if image_bytes is None:
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
        IMAGE_CACHE.ttl(title, temp, 300)
        plt.close(fig)
    else:
        temp = IMAGE_CACHE.get(title)
    temp.seek(0)
    return Response(content=temp.read(), media_type="image/png")


@app.get("/guild_links/{guild_id}",
         tags=["Utils"],
         name="Get clans that are linked to a discord guild")
@limiter.limit("10/second")
async def guild_links(guild_id: int, request: Request, response: Response):
    return {}

@app.get("/all_player_tags",
         tags=["Utils"],
         name="Get a list of all player tags in database")
@limiter.limit("10/second")
async def player_tags(request: Request, response: Response):
    return {}

@app.get("/all_clan_tags",
         tags=["Utils"],
         name="Get a list of all clan tags in database")
@limiter.limit("10/second")
async def clan_tags(request: Request, response: Response):
    return {}


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
         name="Render links to HTML as a page")
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
         name="Get discord links for tags")
@limiter.limit("10/second")
async def discord_link(player_tags: List[str], request: Request, response: Response):
    result = await link_client.get_links(*player_tags)
    return dict(result)


description = """
### Clash of Clans Based API 👑
- No Auth Required
- Ratelimit is 10 req/sec
- Not perfect, stats are collected by polling the Official API
- [Discord Server](https://discord.gg/gChZm3XCrS)
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
    uvicorn.run("main:app", host='0.0.0.0', port=80, ssl_keyfile="/etc/letsencrypt/live/api.clashking.xyz/privkey.pem", ssl_certfile="/etc/letsencrypt/live/api.clashking.xyz/fullchain.pem")
