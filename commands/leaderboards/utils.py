import coc
import disnake

from classes.bot import CustomClient
from classes.DatabaseClient.Classes.player import LegendPlayer



async def hv_player_leaderboard(bot: CustomClient, country_name: str, rankings: list[coc.RankedPlayer], location_emoji: str, embed_color: disnake.Color):
    tag_map = {m.tag: m for m in rankings}
    tags = list(tag_map.keys())

    results = await bot.player_stats.find({'tag': {'$in': list(tags)}}, {'tag': 1, 'legends': 1}).to_list(length=None)
    results = {r.get('tag'): r for r in results}

    full_ranking_data = await bot.leaderboard_db.find({'tag': {'$in': list(tags)}}).to_list(length=None)
    full_ranking_data = {r.get('tag'): r for r in full_ranking_data}

    full_global_ranking = await bot.legend_rankings.find({'tag': {'$in': list(tags)}}).to_list(length=None)
    full_global_ranking = {r.get('tag'): r for r in full_global_ranking}

    player_list = []
    for tag, member in tag_map.items():
        data = results.get(tag)
        if data is None:
            await bot.player_stats.update_one(
                {'tag': tag},
                {
                    '$set': {
                        'paused': False,
                        'name': member.name,
                        'tag': member.tag,
                        'league': member.league.name,
                    }
                },
                upsert=True,
            )
            data = {'tag': member.tag, 'legends': {}}
        default = {
            'country_code': None,
            'country_name': None,
            'local_rank': None,
            'global_rank': None,
        }
        ranking_data = full_ranking_data.get(tag)
        if ranking_data is None:
            ranking_data = default
        if ranking_data.get('global_rank') is None:
            self_global_ranking = full_global_ranking.get(tag)
            if self_global_ranking is not None:
                ranking_data['global_rank'] = self_global_ranking.get('rank')
        player_list.append(LegendPlayer(data=data, ranking_data=ranking_data, api_player=member))

    embeds = []
    text_chunks = []
    text = ''

    for i, player in enumerate(player_list, start=1):
        legend_day = player.get_legend_day()
        emoji = player.ranking.flag if player.ranking.country is not None and country_name == "Global" else bot.emoji.trophy
        text += f'\u200e**{emoji}\u200e{player._.trophies} | \u200e{player._.name}**\n'
        if player._legend_data:
            text += f'-# (#{i}) | {bot.emoji.sword}{legend_day.attack_sum}{legend_day.num_attacks.superscript}'\
                    f' {bot.emoji.shield}{legend_day.defense_sum}{legend_day.num_defenses.superscript}'\
                    f' {bot.emoji.ratio}{player.streak}\n'
        else:
            text += f'-# (#{i}) | {player.tag}\n'
        if i % 25 == 0:
            text_chunks.append(text)
            text = ''

    if text:
        text_chunks.append(text)

    for chunk in text_chunks:
        embed = disnake.Embed(title=f'{location_emoji} {country_name} Top 200 Players', description=chunk, color=embed_color)
        embeds.append(embed)

    return embeds


async def hv_clan_leaderboard(bot: CustomClient, country_name: str, rankings: list[coc.RankedClan], location_emoji: str, family_clan_tags: list[str], embed_color: disnake.Color):
    embeds = []
    text_chunks = []
    text = ''
    family_clan_tags = set(family_clan_tags)

    for i, clan in enumerate(rankings, start=1):
        page_start = (i - 1) // 50 * 50 + 1
        page_end = page_start + 49
        rank_spacing = 4 if page_end >= 100 else 3
        star = '⭐' if clan.tag in family_clan_tags else ''

        text += f'`{str(i).ljust(rank_spacing)}`\u200e{bot.emoji.trophy}\u200e{clan.points} | \u200e{clan.name}{star}\n'
        if i % 50 == 0:
            text_chunks.append(text)
            text = ''

    if text:
        text_chunks.append(text)

    for chunk in text_chunks:
        embed = disnake.Embed(title=f'{location_emoji} {country_name} Top 200 HV Clans', description=chunk, color=embed_color)
        embeds.append(embed)

    return embeds


async def clan_capital_leaderboard(bot: CustomClient, country_name: str, rankings: list[coc.RankedClan], location_emoji: str, family_clan_tags: list[str], embed_color: disnake.Color):
    embeds = []
    text_chunks = []
    text = ''
    family_clan_tags = set(family_clan_tags)

    for i, clan in enumerate(rankings, start=1):
        page_start = (i - 1) // 50 * 50 + 1
        page_end = page_start + 49
        rank_spacing = 4 if page_end >= 100 else 3
        star = '⭐' if clan.tag in family_clan_tags else ''

        text += f'`{str(i).ljust(rank_spacing)}`\u200e{bot.emoji.capital_trophy}\u200e{clan.capital_points} | \u200e{clan.name}{star}\n'
        if i % 50 == 0:
            text_chunks.append(text)
            text = ''

    if text:
        text_chunks.append(text)

    for chunk in text_chunks:
        embed = disnake.Embed(title=f'{location_emoji} {country_name} Top 200 Capital Clans', description=chunk, color=embed_color)
        embeds.append(embed)

    return embeds


async def bb_player_leaderboard(bot: CustomClient, country_name: str, rankings: list[coc.RankedPlayer], location_emoji: str, family_clan_tags: list[str], embed_color: disnake.Color):
    embeds = []
    text_chunks = []
    text = ''
    family_clan_tags = set(family_clan_tags)

    for i, player in enumerate(rankings, start=1):
        page_start = (i - 1) // 50 * 50 + 1
        page_end = page_start + 49
        rank_spacing = 4 if page_end >= 100 else 3
        star = '⭐' if player.clan.tag in family_clan_tags else ''

        text += f'`{str(i).ljust(rank_spacing)}`\u200e{bot.emoji.versus_trophy}\u200e{player.builder_base_trophies} | \u200e{player.name}{star}\n'
        if i % 50 == 0:
            text_chunks.append(text)
            text = ''

    if text:
        text_chunks.append(text)

    for chunk in text_chunks:
        embed = disnake.Embed(title=f'{location_emoji} {country_name} Top 200 BB Players', description=chunk, color=embed_color)
        embeds.append(embed)

    return embeds


async def bb_clan_leaderboard(bot: CustomClient, country_name: str, rankings: list[coc.RankedClan], location_emoji: str, family_clan_tags: list[str], embed_color: disnake.Color):
    embeds = []
    text_chunks = []
    text = ''
    family_clan_tags = set(family_clan_tags)


    for i, clan in enumerate(rankings, start=1):
        page_start = (i - 1) // 50 * 50 + 1
        page_end = page_start + 49
        rank_spacing = 4 if page_end >= 100 else 3

        star = '⭐' if clan.tag in family_clan_tags else ''
        text += f'`{str(i).ljust(rank_spacing)}`\u200e{bot.emoji.versus_trophy}\u200e{clan.builder_base_points} | \u200e{clan.name}{star}\n'
        if i % 50 == 0:
            text_chunks.append(text)
            text = ''

    if text:
        text_chunks.append(text)

    for chunk in text_chunks:
        embed = disnake.Embed(title=f'{location_emoji} {country_name} Top 200 BB Clans', description=chunk, color=embed_color)
        embeds.append(embed)

    return embeds

'''
async def image_board(
    bot: CustomClient,
    clan: coc.Clan,
    server: disnake.Guild,
    type: str,
    limit: int,
    **kwargs,
):
    if clan is None:
        clan_tags = await bot.clan_db.distinct('tag', filter={'server': server.id})
    else:
        clan_tags = [clan.tag]
    if not clan_tags:
        raise MessageException('No clans found')

    start_number = kwargs.get('start_number', 0)
    data = []
    t = time.time()
    if type == 'legend':
        pipeline = [
            {'$match': {'tag': {'$in': clan_tags}}},
            {'$unwind': '$memberList'},
            {'$match': {'memberList.league': 'Legend League'}},
            {'$sort': {'memberList.trophies': -1}},
            {'$limit': limit},
            {'$group': {'_id': None, 'topPlayers': {'$push': '$memberList.tag'}}},
            {'$project': {'_id': 0, 'topPlayers': 1}},
        ]
        result = await bot.basic_clan.aggregate(pipeline=pipeline).to_list(length=None)
        legend_tags = result[0].get('topPlayers', [])
        if not legend_tags:
            raise MessageException('No Legend Players')
        players: List[StatsPlayer] = await bot.get_players(tags=legend_tags, custom=True, use_cache=True)
        players.sort(key=lambda x: x.trophies)
        columns = ['Name', 'Start', 'Atk', 'Def', 'Net', 'Current']
        badges = [player.clan_badge_link() for player in players]
        count = len(players) + 1 + start_number
        for player in players:
            count -= 1
            c = f'{count}.'
            day = player.legend_day()
            if day.net_gain >= 0:
                net_gain = f'+{day.net_gain}'
            else:
                net_gain = f'{day.net_gain}'
            data.append(
                [
                    f"{c:3} {player.name.replace('$','')}",
                    player.trophy_start(),
                    f'{day.attack_sum}{day.num_attacks.superscript}',
                    f'{day.defense_sum}{day.num_defenses.superscript}',
                    net_gain,
                    player.trophies,
                ]
            )
    """elif type == "trophies":
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
            data.append([f"{c:3} {player.name.replace('$','')}", player.donos().donated, player.donos().received, lo, len(player.season_last_online())])"""

    data = {
        'columns': columns,
        'data': data,
        'logo': get_guild_icon(server) if clan is None else clan.badge.url,
        'badge_columns': badges,
        'title': re.sub('[*_`~/"#]', '', f'{(clan or server).name} Top {limit} {type.title()}'),
    }
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
        async with session.post('https://api.clashking.xyz/table', json=data) as response:
            link = await response.json()
        await session.close()
    return f'{link.get("link")}?t={int(pend.now(tz=pend.UTC).timestamp())}'


async def location_components(bot: CustomClient, loc_type: str, **kwargs):
    return None'''

