
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from .utils import fix_tag, capital, leagues, clan_cache_db, clan_stats, basic_clan, clan_history, attack_db
from bson.objectid import ObjectId

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Clan Endpoints"])


#CLAN ENDPOINTS
@router.get("/ban/{server_id}/stats",
         name="All stats for a clan (activity, donations, etc)")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_historical(clan_tag: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    result = await clan_stats.find_one({"tag": clan_tag})
    if result is not None:
        del result["_id"]
    return result



