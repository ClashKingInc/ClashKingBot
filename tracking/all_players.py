

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
from pymongo import UpdateOne, DeleteOne, InsertOne
from datetime import timedelta
from asyncio_throttle import Throttler
from aiohttp import TCPConnector, ClientTimeout, ClientSession
import motor.motor_asyncio
import collections
import aiohttp
import asyncio
import pytz


utc = pytz.utc
load_dotenv()

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"), maxPoolSize=1000)
looper = client.looper
clan_tags = looper.clan_tags

local_client = motor.motor_asyncio.AsyncIOMotorClient("localhost", maxPoolSize=1000)
local_looper = local_client.looper
player = local_looper.player


emails = []
passwords = []
#26-29 (30)
for x in [23, 24, 25, 48, 49, 50, 51, 52]:
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



async def fetch(url, session: aiohttp.ClientSession, headers):
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return (await response.read())
        return None


async def broadcast(keys):
    tag_pipeline = [{"$unwind": "$memberList"},
                    {"$match": {"memberList.townhall": 16}},
                    {"$group": {"_id" : "$memberList.tag"}},

    ]
    tags = await clan_tags.aggregate(tag_pipeline).to_list(length=None)
    all_tags = [x["_id"] for x in tags]

    print(f"got {len(all_tags)} tags")

    keys = deque(keys)
    size_break = 100000
    all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]

    for tag_group in all_tags:
        tasks = []
        connector = TCPConnector(limit=1000, enable_cleanup_closed=True)
        timeout = ClientTimeout(total=1800)
        async with ClientSession(connector=connector, timeout=timeout) as session:
            for tag in tag_group:
                keys.rotate(1)
                tasks.append(fetch(f"https://api.clashofclans.com/v1/players/{tag.replace('#', '%23')}", session, {"Authorization": f"Bearer {keys[0]}"}))
            responses = await asyncio.gather(*tasks)
            await session.close()

        print(f"fetched {len(responses)} responses")
        changes = []
        for response in responses: #type: bytes
            # we shouldnt have completely invalid tags, they all existed at some point
            if response is None:
                continue

            response: dict = ujson.loads(response)
            response["_id"] = response.pop("tag")
            try:
                del response["legendStatistics"]
            except:
                pass
            changes.append(InsertOne(response))

        if changes:
            results = await player.bulk_write(changes, ordered=False)
            print(results.bulk_api_result)




loop = asyncio.get_event_loop()
keys = create_keys()
loop.create_task(broadcast(keys))
loop.run_forever()
