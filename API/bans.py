
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from datetime import datetime
from APIUtils.utils import fix_tag, db_client, token_verify, get_players, limiter, coc_client
from Models.bans import BannedResponse, BannedUser


router = APIRouter(tags=["Ban Endpoints"])


#CLAN ENDPOINTS
@router.post("/ban/{server_id}/add/{player_tag}",
         name="Add a user to the server ban list")
@limiter.limit("10/second")
async def ban_add(server_id: int, player_tag: str, reason: str, added_by: int, api_token: str, request: Request, response: Response) -> BannedUser:
    await token_verify(server_id=server_id, api_token=api_token)
    player = await coc_client.get_player(player_tag=player_tag)
    ban_entry = await db_client.banlist.find_one({"$and": [{"VillageTag": player.tag},{"server": server_id}]})
    if ban_entry is None:
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        ban_entry = {
            "VillageTag": player.tag,
            "DateCreated": dt_string,
            "Notes": reason,
            "server": server_id,
            "added_by": added_by
        }
        await db_client.banlist.insert_one(ban_entry)
    else:
        ban_entry = await db_client.banlist.find_one_and_update({"$and": [{"VillageTag": player.tag}, {"server": server_id}]},
                                                                {'$set': {"Notes": reason, "added_by": added_by}}, upsert=True, return_document=True)

    player_clan = player._raw_data.get("clan")
    if player_clan:
        del player_clan["badgeUrls"]
    ban_entry = ban_entry | {"name" : player.name, "share_link" : player.share_link, "townhall" : player.town_hall, "clan" : player_clan}
    return ban_entry



@router.get("/ban/{server_id}/list",
         name="List of banned users on server",
         response_model=BannedResponse)
@cache(expire=300)
@limiter.limit("3/second")
async def ban_list(server_id: int, request: Request, response: Response, api_token: str = None):
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
            player_clan = player_clan | {"role" : player.role.in_game_name}
            del player_clan["badgeUrls"]

        results.append(ban | {"name" : player.name, "share_link" : player.share_link, "townhall" : player.town_hall, "clan" : player_clan})

    return {"items" : results}
