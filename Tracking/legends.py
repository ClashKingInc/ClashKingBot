import aiohttp
import motor.motor_asyncio
import coc
import os
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://root:matthewanderson3607@65.108.77.253:27017/admin?readPreference=primary&directConnection=true&ssl=false&authMechanism=DEFAULT&authSource=admin")
looper = client.looper
legend_history = looper.legend_history
from pymongo import InsertOne
import asyncio

async def update_legends():
    key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6ImFkY2JjOWFiLTJkODEtNDY4Mi1hNDg0LTU4YzUzOGZkZWI5YyIsImlhdCI6MTY4MDI4OTYzNiwic3ViIjoiZGV2ZWxvcGVyL2FlYjc2MDZhLTYxZTEtNDdiOC1kMGFlLWZhN2ViZGFiZjM0NCIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjQ1Ljc5LjIxOC43OSJdLCJ0eXBlIjoiY2xpZW50In1dfQ.ssgMlQWq25bKIncyhfrASbmi-vlE_L4TuzAxeja-z83l2Tq63MJ2YnD_X--aNEYMV5Qwv2lqwDfHeTHM8v322w"

    #await legend_history.delete_many({"season" : "2022-09"})

    headers = {
        "Accept": "application/json",
        "authorization": f"Bearer {key}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get("https://cocproxy.royaleapi.dev/v1/leagues/29000022/seasons",headers=headers) as response:
            data = await response.json()
            print(data)
            seasons = [entry["id"] for entry in data["items"]]
        await session.close()
    seasons_present = await legend_history.distinct("season")
    print(seasons_present)
    missing = set(seasons) - set(seasons_present)
    print(missing)

    # print(missing)
    for year in missing:
        print(year)
        after = ""
        while after is not None:
            changes = []
            async with aiohttp.ClientSession() as session:
                if after != "":
                    after = f"&after={after}"
                async with session.get(
                        f"https://cocproxy.royaleapi.dev/v1/leagues/29000022/seasons/{year}?limit=100000{after}",
                        headers=headers) as response:
                    items = await response.json()
                    players = items["items"]
                    for player in players:
                        player["season"] = year
                        changes.append(InsertOne(player))
                    try:
                        after = items["paging"]["cursors"]["after"]
                    except:
                        after = None
                await session.close()

            results = await legend_history.bulk_write(changes, ordered=False)
            print(results.bulk_api_result)

loop = asyncio.get_event_loop()
loop.create_task(update_legends())
loop.run_forever()