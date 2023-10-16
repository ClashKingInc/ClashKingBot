import os
import coc
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from collections import defaultdict
from fastapi import  Request, Response, HTTPException, APIRouter, Query
from fastapi_cache.decorator import cache
from typing import List, Annotated
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import fix_tag, capital, leagues, clan_cache_db, clan_stats, basic_clan, clan_history, \
    attack_db, clans_db, gen_season_date, player_stats_db, rankings, player_history, gen_games_season, base_stats

from statistics import mean, median
from datetime import datetime
from pytz import utc
from fastapi.responses import RedirectResponse, HTMLResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Redirect"])
load_dotenv()

@router.get("/p/{player_tag}",
         response_class=RedirectResponse,
         name="Shortform Player Profile URL",
         include_in_schema=False)
async def redirect_fastapi(player_tag: str):
    return f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23{player_tag}"


@router.get("/player",
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



@router.get("/c/{clan_tag}",
         response_class=RedirectResponse,
         name="Shortform Clan Profile URL",
         include_in_schema=False)
async def redirect_fastapi_clan(clan_tag: str):
    return f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{clan_tag}"


@router.get("/base",
         response_class=RedirectResponse,
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

