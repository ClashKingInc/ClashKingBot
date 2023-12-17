
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from datetime import datetime
from APIUtils.utils import  db_client, limiter
from pytz import utc
import dateutil.relativedelta

router = APIRouter(tags=["List Endpoints"])



@router.get("/list/townhalls",
         name="List of current townhall levels")
@cache(expire=300)
@limiter.limit("30/second")
async def list_townhalls(request: Request, response: Response):
    townhalls = await db_client.clans_db.distinct("memberList.townhall")
    return [th for th in townhalls if th is not None and th != 0]


@router.get("/list/seasons",
         name="List of last X seasons")
@cache(expire=300)
@limiter.limit("30/second")
async def list_seasons(request: Request, response: Response, last: int = 12):
    dates = []
    for x in range(0, last + 1):
        end = coc.utils.get_season_end().replace(tzinfo=utc) - dateutil.relativedelta.relativedelta(months=x)
        month = end.month
        if end.month <= 9:
            month = f"0{month}"
        dates.append(f"{end.year}-{month}")
    return dates




