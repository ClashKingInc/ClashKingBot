

async def search_results(bot, query):

    tags = []
    #if search is a player tag, pull stats of the player tag
    player = await bot.getPlayer(query)
    if player is not None:
        tags.append(player)
        return tags


    ttt = await bot.get_tags(query)
    tags.extend(iter(ttt))
    if tags != []:
        results = []
        for tag in tags:
            player = await bot.getPlayer(tag, custom=True)
            if player is None:
                continue
            p = [player.trophies, player]
            results.append(p)
        results = sorted(results, key=lambda l: l[0], reverse=True)
        return [result[1] for result in results]

    return tags




