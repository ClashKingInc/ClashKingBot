import os
import time
from typing import Optional
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from dotenv import load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import UpdateOne, DeleteOne, InsertOne
from datetime import timedelta
from asyncio_throttle import Throttler
from pytz import utc
from statistics import mean
from collections import defaultdict, deque

import motor.motor_asyncio
import collections
import aiohttp
import asyncio
import ujson
import coc
import numpy as np
emails = []
passwords = []
# 14-17 (18)
load_dotenv()
for x in range(14, 18):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(os.getenv("COC_PASSWORD"))



client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))

async def test(keys):


    keys = deque(keys)
    history_db = client.looper.legend_history

    names = await history_db.distinct("season")
    print(names)
    missing = {"2023-08"}

    headers = {
        "Accept": "application/json",
        "authorization": f"Bearer {os.getenv('COC_KEY')}"
    }
    # print(missing)
    for year in missing:
        print(year)
        after = ""
        while after is not None:
            tags = []
            changes = []
            tag_store = {}
            async with aiohttp.ClientSession() as session:
                if after != "":
                    after = f"&after={after}"

                async with session.get(
                        f"https://cocproxy.royaleapi.dev/v1/leagues/29000022/seasons/{year}?limit=100000{after}",
                        headers=headers) as response:
                    items = await response.json()
                    players = items["items"]
                    for player in players:
                        tags.append(player.get("tag"))
                        player["season"] = year
                        tag_store[player.get("tag")] = player
                        # changes.append(InsertOne(player))
                    try:
                        after = items["paging"]["cursors"]["after"]
                    except:
                        after = None
                await session.close()

            timeout = aiohttp.ClientTimeout(total=1800)
            connector = aiohttp.TCPConnector(limit=2000, ttl_dns_cache=300)

            class Player(Struct):
                tag: str
                townHallLevel: int

            print(len(tags))
            tasks = []
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session3:
                for tag in tags:
                    tag = tag.replace("#", "%23")
                    keys.rotate(1)

                    async def fetch(url, session: aiohttp.ClientSession, headers, tag):
                        async with session.get(url, headers=headers) as new_response:
                            if new_response.status == 404:  # remove banned players
                                stored = tag_store[tag]
                                changes.append(InsertOne(stored))
                                return None
                            new_response = await new_response.read()
                            p = decode(new_response, type=Player)
                            stored = tag_store[p.tag]
                            stored["townHallLevel"] = p.townHallLevel
                            changes.append(InsertOne(stored))

                    tasks.append(fetch(f"https://api.clashofclans.com/v1/players/{tag}", session3, {"Authorization": f"Bearer {keys[0]}"}, tag))
                await asyncio.gather(*tasks, return_exceptions=True)
                await session3.close()
            print(f"{len(changes)} changes")
            results = await history_db.bulk_write(changes)
            print(results.bulk_api_result)


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
        ip = \
            json_loads(base64_b64decode(resp_paylaod["temporaryAPIToken"].split(".")[1] + "====").decode("utf-8"))[
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
        # print("Successfully initialised keys for use.")
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

    keys = create_keys()


loop = asyncio.get_event_loop()
keys = create_keys()
loop.create_task(test(keys))
loop.run_forever()
