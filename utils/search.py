
async def search_results(bot, query):

    tags = []
    #if search is a player tag, pull stats of the player tag
    player = await bot.getPlayer(query, custom=True)
    if player is not None:
        tags.append(player)
        return tags


    tag_list = await bot.get_tags(query)
    tags.extend(iter(tag_list))
    if tags != []:
        players = await bot.get_players(tags=tags, custom=True)
        return sorted(players, key=lambda l: l.trophies, reverse=True)

    return tags




