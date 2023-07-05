import pytz
import os
import aiohttp

from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from main import scheduler
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from pymongo import InsertOne

utc = pytz.utc
EMAIL = os.getenv("LEGEND_EMAIL")
PASSWORD = os.getenv("LEGEND_PW")

class LegendCron(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        scheduler.add_job(self.legend_update, 'interval', hours=12)

    async def legend_update(self):
        if not self.bot.user.public_flags.verified_bot:
            return
        keys = await self.create_keys()
        key = keys[0]

        names = await self.bot.history_db.list_collection_names()
        for name in names:
            collection = self.bot.history_db[name]
            await collection.create_index("tag")

        seasons = await self.bot.coc_client.get_seasons(league_id=29000022)
        missing = set(seasons) - set(names)

        headers = {
            "Accept": "application/json",
            "authorization": f"Bearer {key}"
        }
        #print(missing)
        for year in missing:
            print(year)
            after = ""
            while after is not None:
                changes = []
                async with aiohttp.ClientSession() as session:
                    if after != "":
                        after = f"&after={after}"
                    async with session.get(f"https://api.clashofclans.com/v1/leagues/29000022/seasons/{year}?limit=100000{after}", headers=headers) as response:
                        items = await response.json()
                        players = items["items"]
                        for player in players:
                            changes.append(InsertOne(player))
                        try:
                            after = items["paging"]["cursors"]["after"]
                        except:
                            after = None
                    await session.close()

                results = await self.bot.history_db[f"{year}"].bulk_write(changes)

    async def create_keys(self):
        done = False
        while not done:
            try:
                keys = await self.get_key(emails=[EMAIL],passwords=[PASSWORD], key_names="test2", key_count=1)
                done = True
                return keys
            except Exception as e:
                done = False
                print(e)

    async def get_key(self, emails: list, passwords: list, key_names: str, key_count: int):
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

            if len(_keys) < key_count:
                for key in (k for k in keys if k["name"] == key_names and ip not in k["cidrRanges"]):
                    await session.post("https://developer.clashofclans.com/api/apikey/revoke", json={"id": key["id"]})

                while len(_keys) < key_count and len(keys) < 10:
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

        return (total_keys)




def setup(bot: CustomClient):
    bot.add_cog(LegendCron(bot))