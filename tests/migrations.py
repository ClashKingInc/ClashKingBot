
from pymongo import InsertOne


async def migrate_clan_db_simple_schema(bot):
    our_clan_tags = await bot.clan_db.distinct('tag')
    our_clan_stats = await bot.clan_stats.find({'tag': {'$in': our_clan_tags}}, projection={'_id': 0}).to_list(
        length=None
    )
    print(len(our_clan_stats), 'clans')

    player_tags = []
    for clan_stats in our_clan_stats:  # type: dict
        _ = clan_stats.pop('tag')
        for season, player_info in clan_stats.items():
            player_tags += list(player_info.keys())

    player_tags = list(set(player_tags))
    print(len(player_tags), 'tags')
    players = await bot.get_players(tags=player_tags, custom=False)
    players_map = {p.tag: p for p in players}

    bulk_insert = []
    for clan_stats in our_clan_stats:  # type: dict
        clan_tag = clan_stats.pop('tag')
        for season, player_info in clan_stats.items():
            season_data = {'tag': clan_tag, 'season': season, 'members': []}
            member_data = []
            for tag, data in player_info.items():
                api_player = players_map.get(tag)
                if api_player is None:
                    continue
                member_data.append(
                    {
                        'name': api_player.name,
                        'tag': api_player.tag,
                        'townhall': api_player.town_hall,
                        'donated': data.get('donated', 0),
                        'received': data.get('received', 0),
                        'activity': data.get('activity', 0),
                        'gold_looted': data.get('gold_looted', 0),
                        'elixir_looted': data.get('elixir_looted', 0),
                        'dark_elixir_looted': data.get('dark_elixir_looted', 0),
                        'attack_wins': data.get('attack_wins', 0),
                        'clan_games': data.get('clan_games', 0),
                        'trophies': data.get('trophies', 0),
                    }
                )
            season_data['members'] = member_data
            bulk_insert.append(InsertOne(season_data))

    print(len(bulk_insert), 'documents')
    await bot.new_looper.get_collection('new_clan_stats').bulk_write(bulk_insert)
    print('done')


async def migrate_legends(bot):
    print('starting')

    legend_stats_insertions = []
    count = 0
    async for player_stats in bot.player_stats.find({'legends': {'$ne': None}}):
        count += 1
        if count % 5000 == 0:
            try:
                await bot.legends_stats.bulk_write(legend_stats_insertions, ordered=False)
            except Exception as e:
                print(e)
            print(f'{count} players done, {len(legend_stats_insertions)} days accounted')
            legend_stats_insertions = []

        player_tag = player_stats.get('tag')
        legends: dict = player_stats.get('legends')
        if legends:
            for day, data in legends.items():
                if not isinstance(data, dict):
                    continue
                attacks = data.get('attacks', [])
                defenses = data.get('defenses', [])
                offense = sum(attacks)
                defense = sum(defenses)
                ending_trophies = 0

                if data.get('new_attacks'):
                    attacks = data.get('new_attacks', [])
                    offense = sum([x.get('change') for x in attacks])

                if data.get('new_defenses'):
                    defenses = data.get('new_defenses', [])
                    defense = sum([x.get('change') for x in defenses])

                if data.get('new_attacks') or data.get('new_defenses'):
                    all_attacks = data.get('new_attacks', []) + data.get('new_defenses', [])
                    all_attacks.sort(key=lambda x: x.get('time'), reverse=True)
                    if all_attacks:
                        ending_trophies = all_attacks[-1].get('trophies')

                legend_stats_insertions.append(
                    InsertOne(
                        {
                            'tag': player_tag,
                            'day': day,
                            'attacks': attacks,
                            'defenses': defenses,
                            'offense': offense,
                            'defense': defense,
                            'ending_trophies': ending_trophies,
                        }
                    )
                )

    print(f'{len(legend_stats_insertions)} legend days to insert')
    if legend_stats_insertions:
        await bot.legends_stats.bulk_write(legend_stats_insertions, ordered=False)



