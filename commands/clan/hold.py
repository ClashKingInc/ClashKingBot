@register_button('clanhero', parser='_:clan:season:limit')
async def clan_hero_progress(
    bot: CustomClient,
    season: str,
    clan: coc.Clan,
    limit: int = 50,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    if not season:
        season = bot.gen_season_date()

    player_tags = [member.tag for member in clan.members]

    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {
            '$match': {
                '$and': [
                    {'tag': {'$in': player_tags}},
                    {'type': {'$in': list(coc.enums.HERO_ORDER + coc.enums.PETS_ORDER)}},
                    {'time': {'$gte': season_start.timestamp()}},
                    {'time': {'$lte': season_end.timestamp()}},
                ]
            }
        },
        {'$group': {'_id': {'tag': '$tag', 'type': '$type'}, 'num': {'$sum': 1}}},
        {
            '$group': {
                '_id': '$_id.tag',
                'hero_counts': {'$push': {'hero_name': '$_id.type', 'count': '$num'}},
            }
        },
        {
            '$lookup': {
                'from': 'player_stats',
                'localField': '_id',
                'foreignField': 'tag',
                'as': 'name',
            }
        },
        {'$set': {'name': '$name.name'}},
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)

    class ItemHolder:
        def __init__(self, data: dict):
            self.tag = data.get('_id')
            self.name = data.get('name')[0] if data.get('name') else 'unknown'
            self.king = next(
                (item['count'] for item in data['hero_counts'] if item['hero_name'] == 'Barbarian King'),
                0,
            )
            self.queen = next(
                (item['count'] for item in data['hero_counts'] if item['hero_name'] == 'Archer Queen'),
                0,
            )
            self.warden = next(
                (item['count'] for item in data['hero_counts'] if item['hero_name'] == 'Grand Warden'),
                0,
            )
            self.rc = next(
                (item['count'] for item in data['hero_counts'] if item['hero_name'] == 'Royal Champion'),
                0,
            )
            self.pets = sum(
                next(
                    (item['count'] for item in data['hero_counts'] if item['hero_name'] == pet),
                    0,
                )
                for pet in coc.enums.PETS_ORDER
            )
            self.total_upgraded = self.king + self.queen + self.warden + self.rc + self.pets

    all_items = []
    for result in results:
        all_items.append(ItemHolder(data=result))
    all_items = sorted(all_items, key=lambda x: x.total_upgraded, reverse=True)[: min(limit, len(all_items))]
    if not all_items:
        embed = disnake.Embed(description='**No Upgrades Yet**', colour=disnake.Color.red())
    else:
        text = f'BK AQ WD RC Pet Name          \n'
        for item in all_items:
            text += (
                re.sub(
                    r'\b0\b',
                    '-',
                    f'{item.king:<2} {item.queen:<2} {item.warden:<2} {item.rc:<2} {item.pets:<2}',
                    count=6,
                )
                + f'  {item.name[:13]}\n'
            )
        embed = disnake.Embed(description=f'```{text}```', colour=embed_color)
    embed.set_author(name=f'{clan.name} Hero & Pet Upgrades', icon_url=clan.badge.url)

    enums = coc.enums.HERO_ORDER + coc.enums.PETS_ORDER
    # enums = coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER
    pipeline = [
        {
            '$match': {
                '$and': [
                    {'tag': {'$in': player_tags}},
                    {'type': {'$in': enums}},
                    {'time': {'$gte': season_start.timestamp()}},
                    {'time': {'$lte': season_end.timestamp()}},
                ]
            }
        },
        {'$group': {'_id': {'type': '$type'}, 'num': {'$sum': 1}}},
        {'$sort': {'num': -1}},
        {'$limit': 25},
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    text = ''
    total_upgrades = 0
    for result in results:
        type = result.get('_id').get('type')
        emoji = bot.fetch_emoji(type)
        amount = result.get('num')
        total_upgrades += amount
        text += f'{emoji}`{type:15} {amount:3}`\n'

    totals_embed = disnake.Embed(description=f'{text}', colour=embed_color)
    totals_embed.timestamp = datetime.now()
    totals_embed.set_footer(text=f'{season} | {total_upgrades} Upgrades')

    return [embed, totals_embed]


@register_button('clantroops', parser='_:clan:season:limit')
async def troops_spell_siege_progress(
    bot: CustomClient,
    season: str,
    clan: coc.Clan,
    limit: int = 50,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    if not season:
        season = bot.gen_season_date()

    player_tags = [member.tag for member in clan.members]

    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {
            '$match': {
                '$and': [
                    {'tag': {'$in': player_tags}},
                    {
                        'type': {
                            '$in': list(
                                coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER + coc.enums.BUILDER_TROOPS_ORDER
                            )
                        }
                    },
                    {'time': {'$gte': season_start.timestamp()}},
                    {'time': {'$lte': season_end.timestamp()}},
                ]
            }
        },
        {'$group': {'_id': {'tag': '$tag', 'type': '$type'}, 'num': {'$sum': 1}}},
        {
            '$group': {
                '_id': '$_id.tag',
                'counts': {'$push': {'name': '$_id.type', 'count': '$num'}},
            }
        },
        {
            '$lookup': {
                'from': 'player_stats',
                'localField': '_id',
                'foreignField': 'tag',
                'as': 'name',
            }
        },
        {'$set': {'name': '$name.name'}},
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)

    class ItemHolder:
        def __init__(self, data: dict):
            self.tag = data.get('_id')
            self.name = data.get('name', ['unknown'])[0]
            self.troops = sum(
                next(
                    (item['count'] for item in data['counts'] if item['name'] == troop and troop != 'Baby Dragon'),
                    0,
                )
                for troop in list(set(coc.enums.HOME_TROOP_ORDER) - set(coc.enums.SIEGE_MACHINE_ORDER))
            )
            self.spells = sum(
                next(
                    (item['count'] for item in data['counts'] if item['name'] == spell),
                    0,
                )
                for spell in coc.enums.SPELL_ORDER
            )
            self.sieges = sum(
                next(
                    (item['count'] for item in data['counts'] if item['name'] == siege),
                    0,
                )
                for siege in coc.enums.SIEGE_MACHINE_ORDER
            )
            self.builder_troops = sum(
                next(
                    (item['count'] for item in data['counts'] if item['name'] == b_troop and b_troop != 'Baby Dragon'),
                    0,
                )
                for b_troop in coc.enums.BUILDER_TROOPS_ORDER
            )
            self.total_upgraded = self.troops + self.spells + self.sieges + self.builder_troops

    all_items = []
    for result in results:
        all_items.append(ItemHolder(data=result))
    all_items = sorted(all_items, key=lambda x: x.total_upgraded, reverse=True)[: min(limit, len(all_items))]
    if not all_items:
        embed = disnake.Embed(description='**No Upgrades Yet**', colour=embed_color)
    else:
        text = f'HT SP SG BT Name          \n'
        for item in all_items:
            text += f'{item.troops:<2} {item.spells:<2} {item.sieges:<2} {item.builder_troops:<2} {item.name[:13]}\n'
        embed = disnake.Embed(description=f'```{text}```', colour=embed_color)
    embed.set_author(name=f'{clan.name} Hero & Pet Upgrades', icon_url=clan.badge.url)

    enums = coc.enums.HOME_TROOP_ORDER + coc.enums.SPELL_ORDER + coc.enums.BUILDER_TROOPS_ORDER
    pipeline = [
        {
            '$match': {
                '$and': [
                    {'tag': {'$in': player_tags}},
                    {'type': {'$in': enums}},
                    {'time': {'$gte': season_start.timestamp()}},
                    {'time': {'$lte': season_end.timestamp()}},
                ]
            }
        },
        {'$group': {'_id': {'type': '$type'}, 'num': {'$sum': 1}}},
        {'$sort': {'num': -1}},
        {'$limit': 25},
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    text = ''
    total_upgrades = 0
    for result in results:
        type = result.get('_id').get('type')
        emoji = bot.fetch_emoji(type)
        amount = result.get('num')
        total_upgrades += amount
        text += f'{emoji}`{type:15} {amount:3}`\n'

    totals_embed = disnake.Embed(description=f'{text}', colour=embed_color)
    totals_embed.timestamp = datetime.now()
    totals_embed.set_footer(text=f'{season} | {total_upgrades} Upgrades')

    return [embed, totals_embed]


@register_button('clansorted', parser='_:clan:sort_by:limit:townhall')
async def clan_sorted(
    bot: CustomClient,
    clan: coc.Clan,
    sort_by: str,
    townhall: int = None,
    limit: int = 50,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    tags = [m.tag for m in clan.members]
    if townhall is not None:
        tags = [m.tag for m in clan.members if m.town_hall == townhall]
    if not tags:
        raise MessageException('No players to sort, try a lighter search filter')
    players: list[coc.Player] = await bot.get_players(tags=tags, custom=False)

    def get_longest(players, attribute):
        longest = 0
        for player in players:
            if 'ach_' not in attribute and attribute not in ['season_rank', 'heroes']:
                spot = len(str(player.__getattribute__(sort_by)))
            elif 'ach_' in sort_by:
                spot = len(str(player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value))
            elif sort_by == 'season_rank':

                def sort_func(a_player):
                    try:
                        a_rank = a_player.legend_statistics.best_season.rank
                    except:
                        return 0

                spot = len(str(sort_func(player))) + 1
            else:
                spot = len(str(sum([hero.level for hero in player.heroes if hero.is_home_base])))
            if spot > longest:
                longest = spot
        return longest

    og_sort = sort_by
    sort_by = item_to_name[sort_by]
    if 'ach_' not in sort_by and sort_by not in ['season_rank', 'heroes']:
        attr = players[0].__getattribute__(sort_by)
        if isinstance(attr, str) or isinstance(attr, coc.Role) or isinstance(attr, coc.League):
            players = sorted(players, key=lambda x: str(x.__getattribute__(sort_by)))
        else:
            players = sorted(players, key=lambda x: x.__getattribute__(sort_by), reverse=True)
    elif 'ach_' in sort_by:
        players = sorted(
            players,
            key=lambda x: x.get_achievement(name=sort_by.split('_')[-1], default_value=0).value,
            reverse=True,
        )
    elif sort_by == 'season_rank':

        def sort_func(a_player):
            try:
                a_rank = a_player.legend_statistics.best_season.rank
                return a_rank
            except:
                return 10000000

        players = sorted(players, key=sort_func, reverse=False)
    else:
        longest = 3

        def sort_func(a_player):
            a_rank = sum([hero.level for hero in a_player.heroes if hero.is_home_base])
            return a_rank

        players = sorted(players, key=sort_func, reverse=True)

    players = players[:limit]
    longest = get_longest(players=players, attribute=sort_by)

    text = ''
    for count, player in enumerate(players, 1):
        if sort_by in ['role', 'tag', 'heroes', 'ach_Friend in Need', 'town_hall']:
            emoji = bot.fetch_emoji(player.town_hall)
        elif sort_by in ['builder_base_trophies', 'ach_Champion Builder']:
            emoji = bot.emoji.versus_trophy
        elif sort_by in ['trophies', 'ach_Sweet Victory!']:
            emoji = bot.emoji.trophy
        elif sort_by in ['season_rank']:
            emoji = bot.fetch_emoji('Legend League')
        elif sort_by in ['clan_capital_contributions', 'ach_Aggressive Capitalism']:
            emoji = bot.emoji.capital_gold
        elif sort_by in ['exp_level']:
            emoji = bot.emoji.xp
        elif sort_by in ['ach_Nice and Tidy']:
            emoji = bot.emoji.clock
        elif sort_by in ['ach_Heroic Heist']:
            emoji = bot.emoji.dark_elixir
        elif sort_by in ['ach_War League Legend', 'war_stars']:
            emoji = bot.emoji.war_star
        elif sort_by in ['ach_Conqueror', 'attack_wins']:
            emoji = bot.emoji.thick_capital_sword
        elif sort_by in ['ach_Unbreakable']:
            emoji = bot.emoji.shield
        elif sort_by in ['ach_Games Champion']:
            emoji = bot.emoji.clan_games

        spot = f'{count}.'
        if 'ach_' not in sort_by and sort_by not in ['season_rank', 'heroes']:
            text += f'`{spot:3}`{emoji}`{player.__getattribute__(sort_by):{longest}} {player.name[:15]}`\n'
        elif 'ach_' in sort_by:
            text += f"`{spot:3}`{emoji}`{player.get_achievement(name=sort_by.split('_')[-1], default_value=0).value:{longest}} {player.name[:13]}`\n"
        elif sort_by == 'season_rank':
            try:
                rank = player.legend_statistics.best_season.rank
            except:
                rank = ' N/A'
            text += f'`{spot:3}`{emoji}`#{rank:<{longest}} {player.name[:15]}`\n'
        else:
            cum_heroes = sum([hero.level for hero in player.heroes if hero.is_home_base])
            text += f'`{spot:3}`{emoji}`{cum_heroes:3} {player.name[:15]}`\n'

    embed = disnake.Embed(title=f'{clan.name} sorted by {og_sort}', description=text, color=embed_color)

    return embed





@register_button('clanwarpref', parser='_:clan:option')
async def clan_warpreference(
    bot: CustomClient,
    clan: coc.Clan,
    option: str,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    in_count = 0
    out_count = 0
    thcount = defaultdict(int)
    out_thcount = defaultdict(int)

    member_tags = [member.tag for member in clan.members]
    option_convert = {
        'lastoptchange': 'Last Opt Change',
        'lastwar': 'Last War',
        'wartimer': 'War Timer',
    }
    if option == 'lastoptchange':
        pipeline = [
            {'$match': {'$and': [{'tag': {'$in': member_tags}}, {'type': 'warPreference'}]}},
            {'$group': {'_id': '$tag', 'last_change': {'$last': '$time'}}},
        ]
        results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)

        now = int((pend.now(tz=pend.UTC).timestamp()))
        member_stats = {
            result['_id']: smart_convert_seconds(seconds=(now - result['last_change'])) for result in results
        }
    elif option == 'lastwar':
        pipeline = [
            {
                '$match': {
                    '$or': [
                        {'data.clan.members.tag': {'$in': member_tags}},
                        {'data.opponent.members.tag': {'$in': member_tags}},
                    ]
                }
            },
            {
                '$project': {
                    'members': {
                        '$concatArrays': [
                            '$data.clan.members',
                            '$data.opponent.members',
                        ]
                    },
                    'endTime': '$data.endTime',
                }
            },
            {'$unwind': '$members'},
            {'$match': {'members.tag': {'$in': member_tags}}},
            {'$sort': {'endTime': 1}},
            {'$group': {'_id': '$members.tag', 'endTime': {'$last': '$endTime'}}},
        ]
        results: List[dict] = await bot.clan_wars.aggregate(pipeline).to_list(length=None)
        member_stats = {
            result['_id']: smart_convert_seconds(abs(coc.Timestamp(data=result.get('endTime')).seconds_until))
            for result in results
        }

    elif option == 'wartimer':
        pipeline = [
            {'$match': {'_id': {'$in': member_tags}}},
            {'$project': {'_id': 1, 'time': 1}},
        ]
        results: List[dict] = await bot.war_timers.aggregate(pipeline).to_list(length=None)
        member_stats = {}
        now = pend.now(tz=pend.UTC)
        for result in results:
            time: datetime = result.get('time')
            time = time.replace(tzinfo=utc)
            delta = time - now
            seconds = int(delta.total_seconds())
            member_stats[result['_id']] = smart_convert_seconds(seconds=seconds)

    players: List[StatsPlayer] = await bot.get_players(tags=member_tags, custom=True, use_cache=True, fake_results=True)
    players.sort(key=lambda x: (-x.town_hall, x.name), reverse=False)

    opted_in_text = ''
    opted_out_text = ''
    for player in players:
        war_opt_time = member_stats.get(player.tag, '')
        if player.war_opted_in:
            opted_in_text += f'{bot.fetch_emoji(player.town_hall)}`{war_opt_time:7} {player.clear_name[:15]:15}`\n'
            thcount[player.town_hall] += 1
            in_count += 1
        else:
            opted_out_text += f'{bot.fetch_emoji(player.town_hall)}`{war_opt_time:7} {player.clear_name[:15]:15}`\n'
            out_thcount[player.town_hall] += 1
            out_count += 1

    if opted_in_text == '':
        opted_in_text = 'None'
    if opted_out_text == '':
        opted_out_text = 'None'

    in_string = ', '.join(f'Th{index}: {th} ' for index, th in sorted(thcount.items(), reverse=True) if th != 0)
    out_string = ', '.join(f'Th{index}: {th} ' for index, th in sorted(out_thcount.items(), reverse=True) if th != 0)
    legend = f'`{option_convert.get(option)} | Name\n`'
    opted_in_embed = Embed(
        description=f'**{bot.emoji.opt_in}Opted In ({in_count} members)**\n{legend}{opted_in_text}\n',
        color=embed_color,
    )
    opted_out_embed = Embed(
        description=f'**{bot.emoji.opt_out}Opted Out ({out_count} members)**\n{legend}{opted_out_text}\n',
        color=embed_color,
    )

    opted_in_embed.set_author(
        name=f'{clan.name} War Preferences/{option_convert.get(option)}',
        icon_url=clan.badge.url,
    )
    opted_out_embed.set_footer(text=f'In: {in_string}\nOut: {out_string}\n')
    opted_out_embed.timestamp = pend.now(tz=pend.UTC)
    return [opted_in_embed, opted_out_embed]


@register_button('clanactivity', parser='_:clan:season:townhall:limit:sort_by:sort_order')
async def clan_activity(
    bot: CustomClient,
    clan: coc.Clan,
    season: str,
    townhall: int,
    limit: int,
    sort_by: str,
    sort_order: str,
    embed_color: disnake.Color,
):
    season = bot.gen_season_date() if season is None else season
    show_last_online = gen_season_date() == season

    clan_stats = await bot.clan_stats.find_one({'tag': clan.tag}, projection={'_id': 0, f'{season}': 1})
    if not clan_stats:
        is_tracked = await bot.clan_db.find_one({'tag': clan.tag})
        if is_tracked is None:
            raise MessageException(
                f'This clan is not tracked, to have the bot collect this info & more, add {clan.name} to your server with `/addclan`'
            )
        raise MessageException(f'No activity yet, for {clan.name}, for the {season} season')
    clan_stats = clan_stats.get(season, {})
    tags = list(clan_stats.keys())
    players = await bot.get_players(tags=tags, custom=True, use_cache=True)
    map_player = {p.tag: p for p in players}

    holder = namedtuple('holder', ['player', 'name', 'townhall', 'activity', 'lastonline'])
    hold_items = []
    for tag in map_player.keys():
        player = map_player.get(tag)
        hold_items.append(
            holder(
                player=player,
                name=player.name,
                townhall=player.town_hall,
                activity=clan_stats.get(tag, {}).get('activity', 0),
                lastonline=player.last_online if player.last_online else 0,
            )
        )

    if townhall is not None:
        hold_items = [h for h in hold_items if h.townhall == townhall]

    hold_items.sort(
        key=lambda x: x.__getattribute__(sort_by),
        reverse=(sort_order.lower() == 'descending'),
    )
    if len(hold_items) == 0:
        raise MessageException('No players, try a lighter search filter')

    if show_last_online:
        text = '` # ACT   LO    NAME        `\n'
    else:
        text = '` #  ACT    NAME        `\n'

    now = int((pend.now(tz=pend.UTC).timestamp()))
    total_activity = 0
    for count, member in enumerate(hold_items, 1):
        if count <= limit:
            if show_last_online:
                if member.player.last_online is not None:
                    time_text = smart_convert_seconds(seconds=(now - member.player.last_online))
                else:
                    time_text = 'N/A'
                text += f'`{count:2} {member.activity:3} {time_text:7} {member.player.clear_name[:13]:13}`[{create_superscript(member.player.town_hall)}]({member.player.share_link})\n'
            else:
                text += f'`{count:2} {member.activity:4} {member.player.clear_name[:13]:13}`[{create_superscript(member.player.town_hall)}]({member.player.share_link})\n'
        total_activity += member.activity

    embed = disnake.Embed(description=f'{text}', color=embed_color)
    embed.set_author(
        name=f'{clan.name} Top {min(limit, len(hold_items))} Activity',
        icon_url=clan.badge.url,
    )
    embed.set_footer(
        icon_url=bot.emoji.clock.partial_emoji.url,
        text=f'Total Activity: {total_activity} | {season}',
    )
    month = bot.gen_season_date(seasons_ago=24, as_text=False).index(season)
    graph, _ = await daily_graph(bot=bot, clan_tags=[clan.tag], attribute='activity', months=month + 1)
    embed.set_image(file=graph)
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


@register_button('clancapoverview', parser='_:clan:weekend')
async def clan_capital_overview(bot: CustomClient, clan: coc.Clan, weekend: str, embed_color: disnake.Color):
    if weekend is None:
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
    raid_log_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=bot, limit=1)
    if raid_log_entry is None:
        return Embed(
            description='No Raid Weekend Entry Found. Donation info may be available.',
            color=embed_color,
        )
    attack_count = 0
    for member in raid_log_entry.members:
        attack_count += member.attack_count
    embed = disnake.Embed(title=f'{clan.name} Raid Weekend Overview', color=embed_color)
    embed.set_footer(
        text=f"{str(raid_log_entry.start_time.time.date()).replace('-', '/')}-{str(raid_log_entry.end_time.time.date()).replace('-', '/')}",
        icon_url=clan.badge.url,
    )
    embed.add_field(
        name='Overview',
        value=f"- {bot.emoji.capital_gold}{'{:,}'.format(raid_log_entry.total_loot)} Looted\n"
        f"- {bot.fetch_emoji('District_Hall5')}{raid_log_entry.destroyed_district_count} Districts Destroyed\n"
        f'- {bot.emoji.thick_capital_sword}{attack_count}/300 Attacks Complete\n'
        f'- {bot.emoji.people}{len(raid_log_entry.members)}/50 Participants\n'
        f'- Start {bot.timestamp(raid_log_entry.start_time.time.timestamp()).relative}, End {bot.timestamp(raid_log_entry.end_time.time.timestamp()).relative}\n',
        inline=False,
    )
    atk_stats_by_district = defaultdict(list)
    for raid_clan in raid_log_entry.attack_log:
        for district in raid_clan.districts:
            atk_stats_by_district[district.name].append(len(district.attacks))

    offense_district_stats = '```'
    for district, list_atks in atk_stats_by_district.items():
        offense_district_stats += f'{round(mean(list_atks), 2):4} {district}\n'
    offense_district_stats += '```'

    def_stats_by_district = defaultdict(list)
    for raid_clan in raid_log_entry.defense_log:
        for district in raid_clan.districts:
            def_stats_by_district[district.name].append(len(district.attacks))

    def_district_stats = '```'
    for district, list_atks in def_stats_by_district.items():
        def_district_stats += f'{round(mean(list_atks), 2):4} {district}\n'
    def_district_stats += '```'

    embed.add_field(
        'Detailed Stats (Offense)',
        value=f'- Avg Loot/Raid : {B(int(raid_log_entry.total_loot / len(raid_log_entry.attack_log)))}\n'
        f'- Avg Loot/Player: {B(int(raid_log_entry.total_loot / len(raid_log_entry.members)))}\n'
        f'- Avg Hits/Clan: {round(raid_log_entry.attack_count / len(raid_log_entry.attack_log), 2)}\n',
        inline=False,
    )
    embed.add_field(name='(Avg Atks By District, Off)', value=offense_district_stats)
    embed.add_field(name='(Avg Atks By District, Def)', value=def_district_stats)

    attack_summary_text = f'```a=atks, d=districts, l=loot\n'
    for raid_clan in raid_log_entry.attack_log:
        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        attack_summary_text += f'- {raid_clan.name[:12]:12} {raid_clan.attack_count:2}a {raid_clan.destroyed_district_count:1}d {B(sum([d.looted for d in raid_clan.districts])):3}l\n'

    defense_summary_text = '```'
    for raid_clan in raid_log_entry.defense_log:
        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        defense_summary_text += f'- {raid_clan.name[:12]:12} {raid_clan.attack_count:2}a {raid_clan.destroyed_district_count:1}d {B(sum([d.looted for d in raid_clan.districts])):3}l\n'

    attack_summary_text += '```'
    defense_summary_text += '```'
    embed.add_field(name=f'Attack Summary', value=attack_summary_text, inline=False)
    embed.add_field(name='Defense Summary', value=defense_summary_text, inline=False)

    members = sorted(
        list(raid_log_entry.members),
        key=lambda x: x.capital_resources_looted,
        reverse=True,
    )
    top_text = ''
    for count, member in enumerate(members[:3], 1):
        member: coc.raid.RaidMember
        count_conv = {1: 'gold', 2: 'white', 3: 'blue'}
        top_text += f'{bot.get_number_emoji(color=count_conv[count], number=count)}{bot.clean_string(member.name)} {bot.emoji.capital_gold}{member.capital_resources_looted}{create_superscript(member.attack_count)}\n'
    embed.add_field(name='Top 3 Raiders', value=top_text, inline=False)
    file = await generate_raid_result_image(raid_entry=raid_log_entry, clan=clan)
    embed.set_image(file=file)
    return embed


@register_button('clancapdonos', parser='_:clan:weekend')
async def clan_raid_weekend_donation_stats(bot: CustomClient, clan: coc.Clan, weekend: str, embed_color: disnake.Color):
    if weekend is None:
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
    member_tags = [member.tag for member in clan.members]
    capital_raiders = await bot.player_stats.distinct(
        'tag',
        filter={
            '$or': [
                {f'capital_gold.{weekend}.raided_clan': clan.tag},
                {'tag': {'$in': member_tags}},
            ]
        },
    )
    players = await bot.get_players(tags=capital_raiders)

    donated_data = {}
    number_donated_data = {}
    donation_text = ''

    players.sort(key=lambda x: sum(x.clan_capital_stats(week=weekend).donated), reverse=True)
    for player in players[:60]:  # type: StatsPlayer
        sum_donated = 0
        len_donated = 0
        cc_stats = player.clan_capital_stats(week=weekend)
        sum_donated += sum(cc_stats.donated)
        len_donated += len(cc_stats.donated)

        donated_data[player.tag] = sum_donated
        number_donated_data[player.tag] = len_donated

        if player.tag in member_tags:
            donation_text += f'{bot.emoji.capital_gold}`{sum_donated:6} {player.clear_name[:15]:15}`\n'
        else:
            donation_text += f'{bot.emoji.square_x_deny}`{sum_donated:6} {player.clear_name[:15]:15}`\n'

    donation_embed = Embed(
        title=f'**{clan.name} Donation Totals**',
        description=donation_text[:4075],
        color=embed_color,
    )

    donation_embed.set_footer(text=f"Donated: {'{:,}'.format(sum(donated_data.values()))} | Week: {weekend}")
    donation_embed.set_image(None)
    return donation_embed


@register_button('clancapraids', parser='_:clan:weekend')
async def clan_raid_weekend_raid_stats(bot: CustomClient, clan: coc.Clan, weekend: str, embed_color: disnake.Color):
    if weekend is None:
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
    raid_log_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=bot, limit=1)

    if raid_log_entry is None:
        embed = Embed(
            title=f'**{clan.name} Raid Totals**',
            description='No raid found! Donation info may be available.',
            color=embed_color,
        )
        return embed

    total_medals = 0
    total_attacks = defaultdict(int)
    total_looted = defaultdict(int)
    attack_limit = defaultdict(int)
    name_list = {}
    member_tags = [member.tag for member in clan.members]
    members_not_looted = member_tags.copy()

    for member in raid_log_entry.members:
        name_list[member.tag] = member.name
        total_attacks[member.tag] += member.attack_count
        total_looted[member.tag] += member.capital_resources_looted
        attack_limit[member.tag] += member.attack_limit + member.bonus_attack_limit
        try:
            members_not_looted.remove(member.tag)
        except:
            pass

    attacks_done = sum(list(total_attacks.values()))
    attacks_done = max(1, attacks_done)

    total_medals = calc_raid_medals(raid_log_entry.attack_log)

    raid_text = []
    for tag, amount in total_looted.items():
        name = name_list[tag]
        name = bot.clean_string(name)[:13]
        if tag in member_tags:
            raid_text.append(
                [
                    f'\u200e{bot.emoji.capital_gold}`'
                    f'{total_attacks[tag]}/{attack_limit[tag]} '
                    f'{amount:5} {name[:15]:15}`',
                    amount,
                ]
            )
        else:
            raid_text.append(
                [
                    f'\u200e{bot.emoji.square_x_deny}`'
                    f'{total_attacks[tag]}/{attack_limit[tag]} '
                    f'{amount} {name[:15]:15}`',
                    amount,
                ]
            )

    more_to_show = 55 - len(total_attacks.values())
    for member in members_not_looted[:more_to_show]:
        member = coc.utils.get(clan.members, tag=member)
        name = bot.clean_string(member.name)
        raid_text.append([f'{bot.emoji.capital_gold}`{0}' f'/{6} {0:5} {name[:15]:15}`', 0])

    raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
    raid_text = [line[0] for line in raid_text]
    raid_text = '\n'.join(raid_text)

    raid_embed = Embed(title=f'**{clan.name} Raid Totals**', description=raid_text, color=embed_color)

    raid_embed.set_footer(
        text=(
            f'Spots: {len(total_attacks.values())}/50 | '
            f'Attacks: {sum(total_attacks.values())}/300 | '
            f"Looted: {'{:,}'.format(sum(total_looted.values()))} | {raid_log_entry.start_time.time.date()}"
        )
    )
    file = await generate_raid_result_image(raid_entry=raid_log_entry, clan=clan)
    raid_embed.set_image(file=file)
    return raid_embed








@register_button('clangames', parser='_:clan:season:sort_by:sort_order:limit:townhall')
async def clan_games(
    bot: CustomClient,
    clan: coc.Clan,
    season: str,
    sort_by: str,
    sort_order: str,
    limit: int,
    townhall: int,
    embed_color: disnake.Color = EMBED_COLOR_CLASS,
):
    season = bot.gen_games_season() if season is None else season
    clan_stats = await bot.clan_stats.find_one({'tag': clan.tag}, projection={f'{season}': 1})
    if clan_stats is None:
        raise MessageException('No stats tracked for this clan')
    games_season_stats = clan_stats.get(season, {})
    # get the members in the stats that have done clan games, add the current members so that we get 0's, dont worry about duplicates, get_players handles it
    tags = [tag for tag, data in games_season_stats.items() if data.get('clan_games') is not None]
    if season == bot.gen_games_season():
        tags += [m.tag for m in clan.members]
    players = await bot.get_players(tags=tags, custom=True, use_cache=True, fake_results=True)
    if townhall is not None:
        players = [p for p in players if p.townhall == townhall]
    map_player = {p.tag: p for p in players}

    SEASON_START, SEASON_END = games_season_start_end_as_timestamp(season=season)
    pipeline = [
        {
            '$match': {
                '$and': [
                    {'tag': {'$in': list(map_player.keys())}},
                    {'type': 'Games Champion'},
                    {'time': {'$gte': SEASON_START}},
                    {'time': {'$lte': SEASON_END}},
                ]
            }
        },
        {'$sort': {'tag': 1, 'time': 1}},
        {
            '$group': {
                '_id': '$tag',
                'first': {'$first': '$time'},
                'last': {'$last': '$time'},
            }
        },
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    # map to a dict
    member_time_dict = {m['_id']: {'first': m['first'], 'last': m['last']} for m in results}

    holder = namedtuple('holder', ['player', 'name', 'townhall', 'points', 'time'])
    hold_items = []
    for tag in map_player.keys():
        player = map_player.get(tag)
        points = games_season_stats.get(tag, {}).get('clan_games', 0)
        if points is None:
            points = 0
        time_stats = member_time_dict.get(tag)

        seconds_taken = 9999999999
        if time_stats:
            if points < 4000 and is_games():
                time_stats['last'] = int(pend.now(tz=pend.UTC).timestamp())
            first_time = pend.from_timestamp(time_stats['first'], tz=pend.UTC)
            last_time = pend.from_timestamp(time_stats['last'], tz=pend.UTC)
            seconds_taken = (last_time - first_time).total_seconds()
        hold_items.append(
            holder(
                player=player,
                name=player.name,
                townhall=player.town_hall,
                points=points,
                time=seconds_taken,
            )
        )

    hold_items.sort(
        key=lambda x: x.__getattribute__(sort_by.lower()),
        reverse=(sort_order.lower() == 'descending'),
    )
    if len(hold_items) == 0:
        raise MessageException('No players, try a lighter search filter')

    text = '` #      TIME    NAME       `\n'
    total_points = 0
    for count, member in enumerate(hold_items, 1):
        if count <= limit:
            time_text = ''
            if member.time != 9999999999:
                time_text = smart_convert_seconds(seconds=member.time, granularity=2)
            text += f'`{count:2} {member.points:4} {time_text:7} {member.player.clear_name[:13]:13}`[{create_superscript(member.player.town_hall)}]({member.player.share_link})\n'
        total_points += member.points

    embed = disnake.Embed(description=f'{text}', color=embed_color)
    embed.set_author(
        name=f'{clan.name} {min(limit, len(hold_items))} Clan Games',
        icon_url=clan.badge.url,
    )
    embed.set_footer(text=f'Total: {total_points:,} | {season}')
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


def stat_components(bot: CustomClient):
    options = []
    for townhall in reversed(range(6, 16)):
        options.append(
            disnake.SelectOption(
                label=f'Townhall {townhall}',
                emoji=str(bot.fetch_emoji(name=townhall)),
                value=str(townhall),
            )
        )
    th_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder='Select Townhalls',
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )
    options = []
    real_types = ['Fresh Hits', 'Non-Fresh', 'random', 'cwl', 'friendly']
    for count, filter in enumerate(['Fresh Hits', 'Non-Fresh', 'Random Wars', 'CWL', 'Friendly Wars']):
        options.append(disnake.SelectOption(label=f'{filter}', value=real_types[count]))
    filter_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder='Select Filters',
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )
    options = []
    emojis = [
        bot.emoji.animated_clash_swords.partial_emoji,
        bot.emoji.shield.partial_emoji,
        bot.emoji.war_star.partial_emoji,
    ]
    for count, type in enumerate(['Offensive Hitrate', 'Defensive Rate', 'Stars Leaderboard']):
        options.append(disnake.SelectOption(label=f'{type}', emoji=emojis[count], value=type))
    stat_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder='Select Stat Type',
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    dropdown = [
        disnake.ui.ActionRow(th_select),
        disnake.ui.ActionRow(filter_select),
        disnake.ui.ActionRow(stat_select),
    ]
    return dropdown


async def create_offensive_hitrate(
    bot: CustomClient,
    clan: coc.Clan,
    players,
    townhall_level: list = [],
    fresh_type: list = [False, True],
    start_timestamp: int = 0,
    end_timestamp: int = 9999999999,
    war_types: list = ['random', 'cwl', 'friendly'],
    war_statuses=['lost', 'losing', 'winning', 'won'],
):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: StatsPlayer):
        hitrate = await player.hit_rate(
            townhall_level=townhall_level,
            fresh_type=fresh_type,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            war_types=war_types,
            war_statuses=war_statuses,
        )
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        name = emoji.replace_emoji(player.name, '')
        name = str(name)[0:12]
        name = f'{name}'.ljust(12)
        destr = f'{round(hr.average_triples * 100, 1)}%'.rjust(6)
        return [
            f'{player.town_hall_cls.emoji}` {hr_nums} {destr} {name}`\n',
            round(hr.average_triples * 100, 3),
            name,
            hr.num_attacks,
            player.town_hall,
        ]

    for player in players:
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
    text = '`# TH  NUM    HR%    NAME       `\n'
    for count, rank in enumerate(ranked, 1):
        spot_emoji = bot.get_number_emoji(color='gold', number=count)
        text += f'{spot_emoji}{rank[0]}'
    if len(ranked) == 0:
        text = 'No War Attacks Tracked Yet.'
    embed = disnake.Embed(title=f'Offensive Hit Rates', description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append('Fresh')
    if False in fresh_type:
        filter_types.append('Non-Fresh')
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ', '.join(filter_types)
    time_range = 'This Season'
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(
        icon_url=clan.badge.url,
        text=f'{clan.name} | {time_range}\nFilters: {filter_types}',
    )
    return embed


async def create_defensive_hitrate(
    bot: CustomClient,
    clan: coc.Clan,
    players,
    townhall_level: list = [],
    fresh_type: list = [False, True],
    start_timestamp: int = 0,
    end_timestamp: int = 9999999999,
    war_types: list = ['random', 'cwl', 'friendly'],
    war_statuses=['lost', 'losing', 'winning', 'won'],
):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: StatsPlayer):
        hitrate = await player.defense_rate(
            townhall_level=townhall_level,
            fresh_type=fresh_type,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            war_types=war_types,
            war_statuses=war_statuses,
        )
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        hr_nums = f'{hr.total_triples}/{hr.num_attacks}'.center(5)
        name = emoji.replace_emoji(player.name, '')
        name = str(name)[0:12]
        name = f'{name}'.ljust(12)
        destr = f'{round(hr.average_triples * 100, 1)}%'.rjust(6)
        return [
            f'{player.town_hall_cls.emoji} `{hr_nums} {destr} {name}`\n',
            round(hr.average_triples * 100, 3),
            name,
            hr.num_attacks,
            player.town_hall,
        ]

    for player in players:  # type: StatsPlayer
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
    text = '`# TH  NUM    DR%    NAME       `\n'
    for count, rank in enumerate(ranked, 1):
        spot_emoji = bot.get_number_emoji(color='gold', number=count)
        text += f'{spot_emoji}{rank[0]}'
    if len(ranked) == 0:
        text = 'No War Attacks Tracked Yet.'
    embed = disnake.Embed(title=f'Defensive Rates', description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append('Fresh')
    if False in fresh_type:
        filter_types.append('Non-Fresh')
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ', '.join(filter_types)
    time_range = 'This Season'
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(
        icon_url=clan.badge.url,
        text=f'{clan.name} | {time_range}\nFilters: {filter_types}',
    )
    return embed


async def create_stars_leaderboard(
    bot: CustomClient,
    clan: coc.Clan,
    players,
    townhall_level: list = [],
    fresh_type: list = [False, True],
    start_timestamp: int = 0,
    end_timestamp: int = 9999999999,
    war_types: list = ['random', 'cwl', 'friendly'],
    war_statuses=['lost', 'losing', 'winning', 'won'],
):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: StatsPlayer):
        hitrate = await player.hit_rate(
            townhall_level=townhall_level,
            fresh_type=fresh_type,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            war_types=war_types,
            war_statuses=war_statuses,
        )
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        name = str(player.name)[0:12]
        name = f'{name}'.ljust(12)
        stars = f'{hr.total_stars}/{hr.num_attacks}'.center(5)
        destruction = f'{int(hr.total_destruction)}%'.ljust(5)
        return [
            f'{stars} {destruction} {name}\n',
            round(hr.average_triples * 100, 3),
            name,
            hr.total_stars,
            player.town_hall,
        ]

    for player in players:  # type: StatsPlayer
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(ranked, key=lambda l: (-l[-2], -l[1], l[2]), reverse=False)
    text = '```#   â˜…     DSTR%  NAME       \n'
    for count, rank in enumerate(ranked, 1):
        # spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
        count = f'{count}.'.ljust(3)
        text += f'{count} {rank[0]}'
    text += '```'
    if len(ranked) == 0:
        text = 'No War Attacks Tracked Yet.'
    embed = disnake.Embed(title=f'Star Leaderboard', description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append('Fresh')
    if False in fresh_type:
        filter_types.append('Non-Fresh')
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ', '.join(filter_types)
    time_range = 'This Season'
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(
        icon_url=clan.badge.url,
        text=f'{clan.name} | {time_range}\nFilters: {filter_types}',
    )
    return embed


def response_to_line(bot, response, clan):
    clans = response['clans']
    season = response['season']
    tags = [x['tag'] for x in clans]
    stars = {}
    for tag in tags:
        stars[tag] = 0
    rounds = response['rounds']
    for round in rounds:
        wars = round['wars']
        for war in wars:
            main_stars = war['clan']['stars']
            main_destruction = war['clan']['destructionPercentage']
            stars[war['clan']['tag']] += main_stars

            opp_stars = war['opponent']['stars']
            opp_destruction = war['opponent']['destructionPercentage']
            stars[war['opponent']['tag']] += opp_stars

            if main_stars > opp_stars:
                stars[war['clan']['tag']] += 10
            elif opp_stars > main_stars:
                stars[war['opponent']['tag']] += 10
            elif main_destruction > opp_destruction:
                stars[war['clan']['tag']] += 10
            elif opp_destruction > main_destruction:
                stars[war['opponent']['tag']] += 10
    stars = dict(sorted(stars.items(), key=lambda item: item[1], reverse=True))
    place = list(stars.keys()).index(clan.tag) + 1
    league = response['leagueId']
    league_name = [x['name'] for x in war_leagues['items'] if x['id'] == league][0]
    promo = [x['promo'] for x in war_leagues['items'] if x['id'] == league][0]
    demo = [x['demote'] for x in war_leagues['items'] if x['id'] == league][0]

    if place <= promo:
        emoji = '<:warwon:932212939899949176>'
    elif place >= demo:
        emoji = '<:warlost:932212154164183081>'
    else:
        emoji = '<:dash:933150462818021437>'

    end = 'th'
    ends = {1: 'st', 2: 'nd', 3: 'rd'}
    if place <= 3:
        end = ends[place]

    year = season[0:4]
    month = season[5:]
    month = calendar.month_abbr[int(month)]
    # month = month.ljust(9)
    date = f'`{month}`'
    league = str(league_name).replace('League ', '')
    league = league.ljust(14)
    league = f'{league}'

    tier = str(league_name).count('I')

    return (
        f'{emoji} {league_to_emoji(bot=bot, league=league_name)}{SUPER_SCRIPTS[tier]} `{place}{end}` | {date}\n',
        year,
    )
