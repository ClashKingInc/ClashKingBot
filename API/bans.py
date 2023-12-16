
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from slowapi import Limiter
from slowapi.util import get_remote_address
from APIUtils.utils import fix_tag, db_client, token_verify, get_players
from Models.bans import BannedResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Ban Endpoints"])


#CLAN ENDPOINTS
'''@router.post("/ban/{server_id}/add/{player_tag}",
         name="Add a user to the server ban list")
async def ban_add(server_id: int, player_tag: str, api_token: str, request: Request, response: Response):
    result = await db_client.server_db.find_one({"server" : server_id})
    if result is None:
        raise HTTPException(status_code=404, detail="Server Not Found")
    if
    clan_tag = fix_tag(clan_tag)
    result = await clan_stats.find_one({"tag": clan_tag})
    if result is not None:
        del result["_id"]
    return result'''


@router.get("/ban/{server_id}/list",
         name="List of banned users on server")
@limiter.limit("5/second")
async def ban_list(server_id: int, request: Request, response: Response, api_token: str = None) -> BannedResponse:
    await token_verify(server_id=server_id, api_token=api_token)
    bans = await db_client.banlist.find({"server": server_id}).to_list(length=None)
    player_tags = [ban.get("VillageTag") for ban in bans]
    players = await get_players(tags=player_tags)
    results = []
    for ban in bans:
        del ban["_id"]
        player = coc.utils.get(players, tag=ban.get("VillageTag"))
        if not player:
            continue
        player_clan = player._raw_data.get("clan")
        if player_clan:
            del player_clan["badgeUrls"]
        results.append(ban | {"name" : player.name, "share_link" : player.share_link, "townhall" : player.town_hall, "clan" : player_clan})

    return BannedResponse(items=results)




