import gc
import os
import coc
from typing import Optional, List
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from collections import deque

import ujson
from dotenv import load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import UpdateOne, DeleteOne
from datetime import timedelta
from asyncio_throttle import Throttler
from aiohttp import TCPConnector, ClientTimeout, ClientSession
import motor.motor_asyncio
import collections
import aiohttp
import asyncio
import pytz


keys = []
utc = pytz.utc
load_dotenv()

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"), maxPoolSize=1000)
looper = client.looper
clan_tags = looper.clan_tags
rankings = client.new_looper.rankings
deleted_clans = client.new_looper.deleted_clans
throttler = Throttler(rate_limit=1000, period=1)

emails = []
passwords = []
#26-29 (30)
for x in range(23,26):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(os.getenv("COC_PASSWORD"))

async def get_keys(emails: list, passwords: list, key_names: str, key_count: int):
    total_keys = []

    for count, email in enumerate(emails):
        _keys = []
        password = passwords[count]

        session = aiohttp.ClientSession()

        body = {"email": email, "password": password}
        resp = await session.post("https://developer.clashofclans.com/api/login", json=body)
        if resp.status == 403:
            raise RuntimeError(
                "Invalid Credentials"
            )

        resp_paylaod = await resp.json()
        ip = json_loads(base64_b64decode(resp_paylaod["temporaryAPIToken"].split(".")[1] + "====").decode("utf-8"))[
            "limits"][1]["cidrs"][0].split("/")[0]

        resp = await session.post("https://developer.clashofclans.com/api/apikey/list")
        keys = (await resp.json())["keys"]
        _keys.extend(key["key"] for key in keys if key["name"] == key_names and ip in key["cidrRanges"])

        for key in (k for k in keys if ip not in k["cidrRanges"]):
            await session.post("https://developer.clashofclans.com/api/apikey/revoke", json={"id": key["id"]})

        print(len(_keys))
        while len(_keys) < key_count:
            data = {
                "name": key_names,
                "description": "Created on {}".format(datetime.now().strftime("%c")),
                "cidrRanges": [ip],
                "scopes": ["clash"],
            }
            resp = await session.post("https://developer.clashofclans.com/api/apikey/create", json=data)
            key = await resp.json()
            _keys.append(key["key"]["key"])

        if len(keys) == 10 and len(_keys) < key_count:
            print("%s keys were requested to be used, but a maximum of %s could be "
                  "found/made on the developer site, as it has a maximum of 10 keys per account. "
                  "Please delete some keys or lower your `key_count` level."
                  "I will use %s keys for the life of this client.", )

        if len(_keys) == 0:
            raise RuntimeError(
                "There are {} API keys already created and none match a key_name of '{}'."
                "Please specify a key_name kwarg, or go to 'https://developer.clashofclans.com' to delete "
                "unused keys.".format(len(keys), key_names)
            )

        await session.close()
        #print("Successfully initialised keys for use.")
        for k in _keys:
            total_keys.append(k)

    print(len(total_keys))
    return (total_keys)

def create_keys():
    done = False
    while done is False:
        try:
            loop = asyncio.get_event_loop()
            keys = loop.run_until_complete(get_keys(emails=emails,
                                     passwords=passwords, key_names="test", key_count=10))
            done = True
            return keys
        except Exception as e:
            done = False
            print(e)

class League(Struct):
    name : str

class ClanCapital(Struct):
    capitalHallLevel: Optional[int] = 0

class Location(Struct):
    name: str
    id: int

class Members(Struct):
    tag: str
    name: str
    expLevel: int
    trophies: int
    role: str
    builderBaseTrophies: int
    donations: int
    donationsReceived: int
    townHallLevel: int
    league: League


class Clan(Struct):
    name: str
    tag: str
    type: str
    clanLevel: int
    isWarLogPublic: bool
    members: int
    clanPoints: int
    clanCapitalPoints: int
    capitalLeague: League
    warLeague: League
    warWinStreak: int
    warWins: int
    clanCapital: ClanCapital
    memberList : List[Members]
    location: Optional[Location] = None


async def fetch(url, session: aiohttp.ClientSession, headers):
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return (await response.read())
        return None


async def broadcast(keys):

    x = 0
    while True:
        try:
            keys = deque(keys)
            if x % 10 == 0:
                pipeline = [{"$match" : {"$or" : [{"members" : {"$lt" : 10}}, {"level" : {"$lt" : 3}}, {"capitalLeague" : "Unranked"}]}}, { "$group" : { "_id" : "$tag" } } ]
            else:
                pipeline = [{"$match": {"$nor" : [{"members" : {"$lt" : 10}}, {"level" : {"$lt" : 3}}, {"capitalLeague" : "Unranked"}]}}, {"$group": {"_id": "$tag"}}]
            x += 1
            all_tags = [x["_id"] for x in (await clan_tags.aggregate(pipeline).to_list(length=None))]
            print(f"{len(all_tags)} tags")
            size_break = 50000
            all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]

            for tag_group in all_tags:
                tasks = []
                connector = TCPConnector(limit=250, enable_cleanup_closed=True)
                timeout = ClientTimeout(total=1800)
                async with ClientSession(connector=connector, timeout=timeout) as session:
                    for tag in tag_group:
                        keys.rotate(1)
                        tasks.append(fetch(f"https://api.clashofclans.com/v1/clans/{tag.replace('#', '%23')}", session, {"Authorization": f"Bearer {keys[0]}"}))
                    responses = await asyncio.gather(*tasks)
                    await session.close()
                print(f"fetched {len(responses)} responses")
                changes = []
                raid_week = gen_raid_date()
                season = gen_season_date()
                for response in responses: #type: bytes
                    # we shouldnt have completely invalid tags, they all existed at some point
                    if response is None:
                        continue
                    try:
                        clan = decode(response, type=Clan)
                        if clan.members == 0:
                            await deleted_clans.insert_one(ujson.loads(response))
                            changes.append(DeleteOne({"tag": clan.tag}))
                        else:
                            members = []
                            for member in clan.memberList:
                                members.append({"name": member.name, "tag" : member.tag, "role" : member.role, "expLevel" : member.expLevel, "trophies" : member.trophies,
                                                "townhall" : member.townHallLevel, "league" : member.league.name,
                                        "builderTrophies" : member.builderBaseTrophies, "donations" : member.donations, "donationsReceived" : member.donationsReceived})
                            changes.append(UpdateOne({"tag": clan.tag},
                                                          {"$set":
                                                               {"name": clan.name,
                                                                "members" : clan.members,
                                                                "level" : clan.clanLevel,
                                                                "type" : clan.type,
                                                                "location" : {"id" :clan.location.id if clan.location else clan.location, "name" : clan.location.name if clan.location else clan.location},
                                                                "clanCapitalPoints" : clan.clanCapitalPoints,
                                                                "clanPoints" : clan.clanPoints,
                                                                "capitalLeague" : clan.capitalLeague.name,
                                                                "warLeague" : clan.warLeague.name,
                                                                "warWinStreak" : clan.warWinStreak,
                                                                "warWins" : clan.warWins,
                                                                "clanCapitalHallLevel" : clan.clanCapital.capitalHallLevel,
                                                                "isValid" : clan.members >= 5,
                                                                "openWarLog" : clan.isWarLogPublic,
                                                                f"changes.clanCapital.{raid_week}": {"trophies" : clan.clanCapitalPoints, "league" : clan.capitalLeague.name},
                                                                f"changes.clanWarLeague.{season}": {"league": clan.warLeague.name},
                                                                "memberList": members
                                                                },
                                                           },
                                                          upsert=True))
                    except Exception:
                        continue

                if changes:
                    results = await clan_tags.bulk_write(changes, ordered=False)
                    print(results.bulk_api_result)

            ranking_pipeline = [{"$unwind": "$memberList"},
             {"$match": {"memberList.league": "Legend League"}},
             {"$project": {"name": "$memberList.name", "tag": "$memberList.tag",
                           "trophies": "$memberList.trophies", "townhall": "$memberList.townhall"}},
             {"$unset": ["_id"]},
             {"$setWindowFields": {
                 "sortBy": {"trophies": -1},
                 "output": {
                     "rank": {"$rank": {}}
                 }
             }},
             {"$out": {"db": "new_looper", "coll": "legend_rankings"}}
             ]
            await clan_tags.aggregate(ranking_pipeline)
            print("UPDATED RANKING")
        except Exception:
            continue


def gen_raid_date():
    now = datetime.utcnow().replace(tzinfo=utc)
    current_dayofweek = now.weekday()
    if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
            current_dayofweek == 0 and now.hour < 7):
        if current_dayofweek == 0:
            current_dayofweek = 7
        fallback = current_dayofweek - 4
        raidDate = (now - timedelta(fallback)).date()
        return str(raidDate)
    else:
        forward = 4 - current_dayofweek
        raidDate = (now + timedelta(forward)).date()
        return str(raidDate)

def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=utc).date()
    month = end.month
    if end.month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"

loop = asyncio.get_event_loop()
keys = create_keys()
loop.create_task(broadcast(keys))
loop.run_forever()
