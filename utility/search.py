from classes.bot import CustomClient
from utility.general import create_superscript

async def search_results(bot: CustomClient, query, use_cache=True):

    tags = []
    #if search is a player tag, pull stats of the player tag
    player = await bot.getPlayer(query, custom=True)
    if player is not None:
        tags.append(player)
        return tags


    tag_list = await bot.get_tags(query)
    tags.extend(iter(tag_list))
    if tags != []:
        players = await bot.get_players(tags=tags, custom=True, use_cache=use_cache)
        return sorted(players, key=lambda l: l.trophies, reverse=True)

    return tags



async def search_name_with_tag(bot: CustomClient, query: str, poster=False):
    names = []
    if query == "":
        pipeline = [
            {"$match" : {"league" : "Legend League"}},
            {"$limit": 25}]
    else:
        pipeline= [
            {
            "$search": {
                "index": "player_search",
                "autocomplete": {
                    "query": query,
                    "path": "name",
                },
            }
            },
            {"$match" : {"league" : "Legend League"}},
            {"$limit": 25}
        ]
    results = await bot.player_search.aggregate(pipeline=pipeline).to_list(length=None)
    for document in results:
        league = document.get("league")
        if league == "Unknown":
            league = "Unranked"
        league = league.replace(" League", "")
        names.append(f'{create_superscript(document.get("th"))}{document.get("name")} ({league})' + " | " + document.get("tag"))
    return names



async def family_names(bot: CustomClient, query: str, guild):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    names = []
    if query == "":
        pipeline = [
            {"$match": {"clan": {"$in" : clan_tags}}},
            {"$limit": 25}
        ]
    else:
        pipeline = [
            {
            "$search": {
                "index": "player_search",
                "autocomplete": {
                    "query": query,
                    "path": "name",
                },
            }
            },
            {"$match": {"clan": {"$in" : clan_tags}}},
            {"$limit": 25}
        ]
    results = await bot.player_search.aggregate(pipeline=pipeline).to_list(length=None)
    for document in results:
        league = document.get("league")
        if league == "Unknown":
            league = "Unranked"
        league = league.replace(" League", "")
        names.append(f'{create_superscript(document.get("th"))}{document.get("name")} ({league})' + " | " + document.get("tag"))
    return names


async def all_names(bot: CustomClient, query: str):
    names = []
    if query == "":
        pipeline = [
            {"$match": {}},
            {"$limit": 25}
        ]
    else:
        pipeline = [
            {
            "$search": {
                "index": "player_search",
                "autocomplete": {
                    "query": query,
                    "path": "name",
                },
            }
            },
            {"$limit": 25}
        ]
    results = await bot.player_search.aggregate(pipeline=pipeline).to_list(length=None)
    for document in results:
        league = document.get("league")
        if league == "Unknown":
            league = "Unranked"
        league = league.replace(" League", "")
        names.append(f'{create_superscript(document.get("th"))}{document.get("name")} ({league})' + " | " + document.get("tag"))
    return names




