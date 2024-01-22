import time

import coc
import disnake

from CustomClasses.CustomBot import CustomClient
from typing import List
from exceptions.CustomExceptions import MessageException
import pendulum as pend
import re
from CustomClasses.CustomPlayer import MyCustomPlayer
import aiohttp
import ujson
from utility.general import get_guild_icon

async def image_board(bot: CustomClient, clan: coc.Clan, server: disnake.Guild, type: str, limit: int, **kwargs):
    if clan is None:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": server.id})
    else:
        clan_tags = [clan.tag]
    if not clan_tags:
        raise MessageException("No clans found")

    start_number = kwargs.get("start_number", 0)
    data = []
    t = time.time()
    if type == "legend":
        pipeline = [
            {"$match" : {"tag" : {"$in" : clan_tags}}},
            {"$unwind": "$memberList"},
            {"$match" : {"memberList.league" : "Legend League"}},
            {"$sort": {"memberList.trophies": -1}},
            {"$limit": limit},
            {"$group" : {"_id" : None, "topPlayers" : {"$push" : "$memberList.tag"}}},
            {"$project":{"_id": 0, "topPlayers" : 1}}
        ]
        result = await bot.basic_clan.aggregate(pipeline=pipeline).to_list(length=None)
        legend_tags = result[0].get("topPlayers", [])
        if not legend_tags:
            raise MessageException("No Legend Players")
        players: List[MyCustomPlayer] = await bot.get_players(tags=legend_tags, custom=True, use_cache=True)
        players.sort(key=lambda x : x.trophies )
        columns = ['Name', "Start", "Atk", "Def", "Net", "Current"]
        badges = [player.clan_badge_link() for player in players]
        count = len(players) + 1 + start_number
        for player in players:
            count -= 1
            c = f"{count}."
            day = player.legend_day()
            if day.net_gain >= 0:
                net_gain = f"+{day.net_gain}"
            else:
                net_gain = f"{day.net_gain}"
            data.append([f"{c:3} {player.name.replace('$','')}", player.trophy_start(), f"{day.attack_sum}{day.num_attacks.superscript}", f"{day.defense_sum}{day.num_defenses.superscript}", net_gain, player.trophies])


    '''elif type == "trophies":
        columns = ['Name', "Trophies", "League", "Builder", "B-League"]
        basic_clans = await bot.basic_clan.find({"tag": {"$in": clan_tags}}, projection={"memberList": 1}).to_list(length=None)

        badges = [player.league.icon.url if player.league.name != "Unranked" else "https://clashking.b-cdn.net/unranked.png" for player in players]
        count = len(players) + 1
        for player in players:
            count -= 1
            c = f"{count}."
            data.append([f"{c:3} {player.name.replace('$','')}", player.trophies, str(player.league).replace(" League", ""), player.versus_trophies, str(player.builder_league).replace(" League", "")])

    elif type == "activities":
        columns = ['Name', "Donated", "Received", "Last Online", "Activity"]
        badges = [player.league.icon.url if player.league.name != "Unranked" else "https://clashking.b-cdn.net/unranked.png" for player in players]
        count = len(players) + 1
        now_seconds = int(datetime.now().timestamp())
        for player in players:
            count -= 1
            c = f"{count}."
            lo = convert_seconds(now_seconds - player.last_online) if player.last_online else "N/A"
            data.append([f"{c:3} {player.name.replace('$','')}", player.donos().donated, player.donos().received, lo, len(player.season_last_online())])'''

    data = {
        "columns" : columns,
        "data" : data,
        "logo" : get_guild_icon(server) if clan is None else clan.badge.url,
        "badge_columns" : badges,
        "title" : re.sub('[*_`~/"#]', '', f"{(clan or server).name} Top {limit} {type.title()}"),
    }
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
        async with session.post("https://api.clashking.xyz/table", json=data) as response:
            link = await response.json()
        await session.close()
    return f'{link.get("link")}?t={int(pend.now(tz=pend.UTC).timestamp())}'

