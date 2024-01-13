import coc
import sys
sys.path.append("..")
import settings
import asyncio
from datetime import datetime
from pymongo import UpdateOne, InsertOne
import os
import motor.motor_asyncio
from redis import asyncio as redis

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_LOGIN"))
redis = redis.Redis(host='85.10.200.219', port=6379, db=2, password=os.getenv("REDIS_PW"), retry_on_timeout=True, max_connections=25, retry_on_error=[redis.ConnectionError])

new_looper = client.new_looper
clan_history = new_looper.clan_history
clan_cache = new_looper.clan_cache
join_leave_history = new_looper.clan_join_leave


IS_UPDATE = {}

def get_changes(previous_response: dict, response: dict):
    new_json = {}
    fields_to_update = []
    for key, item in response.items():
        old_item = previous_response.get(key)
        if old_item != item and key != "_response_retry":
            fields_to_update.append(key)
        not_ok_fields = {"badgeUrls", "memberList", "_response_retry"}
        if key in not_ok_fields:
            continue
        if old_item != item:
            new_json[key] = item
    return (new_json, fields_to_update)


@coc.ClanEvents.any_change()
async def any_change(old_clan: coc.Clan, new_clan:coc.Clan):
    old_json = old_clan._raw_data
    new_json = new_clan._raw_data

    bulk_insert = []
    bulk_join_leave = []

    changes, fields_to_update = get_changes(old_json, new_json)
    if changes:
        for key, item in changes.items():
            bulk_insert.append(InsertOne({"tag": new_clan.tag, "type": key, "value": item, "time": int(datetime.now().timestamp())}))

    await redis.set(name=new_clan.tag, value=new_json)

    current_tags = set(n.tag for n in old_clan.members)
    new_current_tags = set(n.tag for n in new_clan.members)
    members_joined = (n for n in new_clan.members if n.tag not in current_tags)
    members_left = (n for n in old_clan.members if n.tag not in new_current_tags)
    for member in members_joined:
        bulk_join_leave.append(InsertOne({
            "tag" : member.tag,
            "clan" : new_clan.tag,
            "dir" : "Join",
            'time' : int(datetime.now().timestamp())
        }))
    for member in members_left:
        bulk_join_leave.append(InsertOne({
            "tag" : member.tag,
            "clan" : new_clan.tag,
            "dir" : "Leave",
            'time' : int(datetime.now().timestamp())
        }))

    if bulk_insert != []:
        await clan_history.bulk_write(bulk_insert)

    if bulk_join_leave != []:
        await join_leave_history.bulk_write(bulk_join_leave)


@coc.ClanEvents.member_join()
async def member_join(member: coc.ClanMember, old_clan: coc.Clan, new_clan: coc.Clan):
    clan_tasks = []
    async def send_ws(ws, json):
        try:
            await ws.send_json(json)
        except:
            try:
                settings.CLAN_CLIENTS.remove(ws)
            except:
                pass

    json_data = {"type": "member_join",
                 "member": member._raw_data,
                 "old_clan" : old_clan._raw_data,
                 "clan": new_clan._raw_data}

    for client in settings.CLAN_CLIENTS.copy():
        task = asyncio.ensure_future(send_ws(ws=client, json=json_data))
        clan_tasks.append(task)
    await asyncio.gather(*clan_tasks, return_exceptions=False)

@coc.ClanEvents.member_leave()
async def member_leave(member: coc.ClanMember, old_clan: coc.Clan, new_clan: coc.Clan):
    clan_tasks = []
    async def send_ws(ws, json):
        try:
            await ws.send_json(json)
        except:
            try:
                settings.CLAN_CLIENTS.remove(ws)
            except:
                pass

    json_data = {"type": "member_leave",
                 "member": member._raw_data,
                 "old_clan": old_clan._raw_data,
                 "clan": new_clan._raw_data}

    for client in settings.CLAN_CLIENTS.copy():
        task = asyncio.ensure_future(send_ws(ws=client, json=json_data))
        clan_tasks.append(task)
    await asyncio.gather(*clan_tasks, return_exceptions=False)

@coc.ClanEvents.bulk_donations()
async def member_donos(old_clan: coc.Clan, clan: coc.Clan):
    clan_tasks = []
    async def send_ws(ws, json):
        try:
            await ws.send_json(json)
        except:
            try:
                settings.CLAN_CLIENTS.remove(ws)
            except:
                pass

    json_data = {"type": "all_member_donations", "old_clan" : old_clan._raw_data, "new_clan" : clan._raw_data}

    for client in settings.CLAN_CLIENTS.copy():
        task = asyncio.ensure_future(send_ws(ws=client, json=json_data))
        clan_tasks.append(task)
    await asyncio.gather(*clan_tasks, return_exceptions=False)