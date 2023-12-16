import os
import ujson

from fastapi import FastAPI, Request, Response, Query, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Leagues"])


@router.get("/builderbaseleagues",
         tags=["Leagues"],
         name="Builder Base Leagues w/ Icons")
@cache(expire=300)
@limiter.limit("30/second")
async def builder_base_leagues(request: Request, response: Response):
    file_name = "builder_league.json"
    file_path = os.getcwd() + "/" + file_name
    with open(file_path) as json_file:
        data = ujson.load(json_file)
        for item in data.get("items"):
            league = item.get("name")
            split = league.split(" ")
            if len(split) == 3:
                if "IV" in split[-1]:
                    tier = 4
                elif "V" in split[-1]:
                    tier = 5
                else:
                    tier = len(split[-1])
            else:
                tier = 1
            item["iconUrls"] = {"medium" : f"https://cdn.clashking.xyz/clash-assets/builder_base_{split[0].lower()}_{split[1].lower()}_{tier}.png"}
        return data