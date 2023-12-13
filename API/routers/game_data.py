import coc
import os
import ujson
from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List, Union
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import fix_tag, capital, leagues, player_trophies, player_versus_trophies, clan_trophies, capital_trophies, clan_versus_trophies
from fastapi.responses import FileResponse


limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Game Data"])

@router.get("/assets",
         name="Link to download a zip with all assets")
@limiter.limit("5/second")
async def assets(request: Request, response: Response):
    return {"download-link" : "https://cdn.clashking.xyz/Out-Sprites.zip"}



@router.get("/json/{type}",
         name="View json game data (/json/list, for list of types)")
@limiter.limit("5/second")
async def json(type: str, request: Request, response: Response):
    if type == "list":
        return {"files" : ["troops", "heroes", "hero_equipment", "spells", "buildings", "pets", "supers", "townhalls", "translations"]}
    file_name = f"game-json/{type}.json"
    file_path = os.getcwd() + "/" + file_name
    with open(file_path) as json_file:
        data = ujson.load(json_file)
        return data