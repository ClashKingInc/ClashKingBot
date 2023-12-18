import json
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from APIUtils.utils import  db_client, token_verify, limiter

from bson import json_util

router = APIRouter(tags=["Server Settings"])


@router.get("/server-settings/{server_id}",
         name="Settings on a server")
@limiter.limit("10/second")
async def server_settings(server_id: int, request: Request, response: Response, api_token: str):
    await token_verify(server_id=server_id, api_token=api_token)
    pipeline = [
        {"$match": {"server": server_id}},
        {"$lookup": {"from": "legendleagueroles", "localField": "server", "foreignField": "server", "as": "eval.league_roles"}},
        {"$lookup": {"from": "evalignore", "localField": "server", "foreignField": "server", "as": "eval.ignored_roles"}},
        {"$lookup": {"from": "generalrole", "localField": "server", "foreignField": "server", "as": "eval.family_roles"}},
        {"$lookup": {"from": "linkrole", "localField": "server", "foreignField": "server", "as": "eval.not_family_roles"}},
        {"$lookup": {"from": "townhallroles", "localField": "server", "foreignField": "server", "as": "eval.townhall_roles"}},
        {"$lookup": {"from": "builderhallroles", "localField": "server", "foreignField": "server", "as": "eval.builderhall_roles"}},
        {"$lookup": {"from": "achievementroles", "localField": "server", "foreignField": "server", "as": "eval.achievement_roles"}},
        {"$lookup": {"from": "statusroles", "localField": "server", "foreignField": "server", "as": "eval.status_roles"}},
        {"$lookup": {"from": "builderleagueroles", "localField": "server", "foreignField": "server", "as": "eval.builder_league_roles"}},
        {"$lookup": {"from": "clans", "localField": "server", "foreignField": "server", "as": "clans"}},
    ]
    results = await db_client.server_db.aggregate(pipeline).to_list(length=1)
    if not results:
        raise HTTPException(status_code=404, detail="Server Not Found")
    results = json.loads(json_util.dumps(results[0]))
    return results
