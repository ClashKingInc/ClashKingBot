
from disnake.ext import commands
from utils.clash import getPlayer, getTags, client

usafam = client.usafam
clans = usafam.clans



async def search_results( ctx, query):

    tags = []
    #if search is a player tag, pull stats of the player tag
    player = await getPlayer(query)
    if player is not None:
        tags.append(player.tag)
        return tags


    ttt = await getTags(ctx, query)
    for tag in ttt:
        tags.append(tag)
    if tags != []:
        results = []
        for tag in tags:
            p = []
            player = await getPlayer(tag)
            if player is None:
                continue
            p.append(player.trophies)
            p.append(player.tag)
            results.append(p)
        results = sorted(results, key=lambda l: l[0], reverse=True)
        new_tags = []
        for result in results:
            new_tags.append(result[1])
        return new_tags

    return tags


