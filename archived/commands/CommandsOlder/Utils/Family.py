import disnake
import coc
import asyncio

from coc.raid import RaidLogEntry
from datetime import datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake.ext.commands import AutoShardedBot as CustomClient
from classes.player import MyCustomPlayer, ClanCapitalWeek
from utility.general import create_superscript
from utility.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry, calc_raid_medals
from utility.constants import item_to_name, SHORT_PLAYER_LINK, leagues
from utility.clash import cwl_league_emojis
from classes.enum import TrophySort
from collections import defaultdict
from typing import List
from pytz import utc


async def create_family_clans(bot: CustomClient, guild: disnake.Guild, embed_color: disnake.Color = disnake.Color.green()):
    categories: list = await bot.clan_db.distinct("category", filter={"server": guild.id})
    server_db = await bot.server_db.find_one({"server": guild.id})
    sorted_categories = server_db.get("category_order")
    if sorted_categories is not None:
        missing_cats = list(set(categories).difference(sorted_categories))
        categories = sorted_categories + missing_cats
    categories.insert(0, "All Clans")

    results = await bot.clan_db.find({"server": guild.id}).sort([("category", 1), ("name", 1)]).to_list(length=100)
    results_dict = defaultdict(list)
    clan_tags = []
    for result in results:
        results_dict[result.get("category")].append(result)
        clan_tags.append(result.get("tag"))


    text = ""
    member_count = 0
    clans = await bot.get_clans(tags=clan_tags)
    no_emoji = False
    if len(clans) > 25:
        no_emoji = True
    for category in categories:
        if category == "All Clans":
            continue
        clan_result = results_dict.get(category, [])
        if not clan_result:
            continue
        text += f"__**{category}**__\n"
        clan_result = [c for clan in clan_result if (c := coc.utils.get(clans, tag=clan.get("tag")))]
        clan_result.sort(key=lambda x: x.war_league.id, reverse=True)
        for clan in clan_result:
            #leader = coc.utils.get(clan.members, role=coc.Role.leader)
            #text += f"[{clan.name}]({clan.share_link}) | ({clan.member_count}/50)\n" \
                    #f"**Leader:** {leader.name}\n\n"
            if not no_emoji:
                text += f"{cwl_league_emojis(clan.war_league.name)}{clan.name} | ({clan.member_count}/50)\n"
            else:
                text += f"{clan.name} | ({clan.member_count}/50)\n"
            member_count += clan.member_count

        #master_embed.add_field(name=, value=text, inline=False)

    master_embed = disnake.Embed(
        description=text, color=embed_color)
    if guild.icon:
        master_embed.set_thumbnail(url=guild.icon.url)
    master_embed.set_footer(icon_url=guild.icon.url if guild.icon is not None else bot.user.avatar.url,
                            text=f"{guild.name} | {member_count} Players/{len(clans)} Clans")
    return master_embed


async def create_leagues(bot: CustomClient, guild: disnake.Guild, type: str):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    clans: List[coc.Clan] = await bot.get_clans(tags=clan_tags)

    if not clans:
        return disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())

    clans_by_league = defaultdict(list)
    if type == "Capital":
        clans = sorted(clans, key=lambda l:  l.capital_points, reverse=True)
        [clans_by_league[clan.capital_league.name].append(clan) for clan in clans]
    elif type == "CWL":
        [clans_by_league[clan.war_league.name].append(clan) for clan in clans]

    main_embed = disnake.Embed(title=f"__**{guild.name} {type} Leagues**__",
                               color=disnake.Color.green())
    if guild.icon is not None:
        main_embed.set_thumbnail(url=guild.icon.url)

    for league in leagues:
        text = ""
        league_clans: List[coc.Clan] = clans_by_league.get(league, [])
        if not league_clans:
            continue
        for clan in league_clans:
            if type == "Capital":
                text += f"{bot.emoji.capital_trophy}`{clan.capital_points:4}` {clan.name}\n"
            elif type == "CWL":
                text += f"{clan.name}\n"
        main_embed.add_field(name=f"**{league}**", value=text, inline=False)

    return main_embed


async def create_raids(bot: CustomClient, guild: disnake.Guild):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    if not clan_tags:
        embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
        return embed

    clans = await bot.get_clans(tags=clan_tags)

    tasks = []
    async def get_raid_stuff(clan):
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=bot, limit=2)
        return [clan, weekend_raid_entry]

    for clan in clans:
        if clan is None:
            continue
        task = asyncio.ensure_future(get_raid_stuff(clan))
        tasks.append(task)

    raid_list = await asyncio.gather(*tasks)
    raid_list = [r for r in raid_list if r[1] is not None]

    if len(raid_list) == 0:
        embed = disnake.Embed(description="No clans currently in raid weekend", color=disnake.Color.red())
        return embed

    embed = disnake.Embed(description=f"**{guild.name} Current Raids**", color=disnake.Color.green())

    raid_list = sorted(raid_list, key=lambda l: l[0].name, reverse=False)
    for raid_item in raid_list:
        clan: coc.Clan = raid_item[0]
        raid: RaidLogEntry = raid_item[1]

        medals = calc_raid_medals(raid.attack_log)
        emoji = await bot.create_new_badge_emoji(url=clan.badge.url)
        hall_level = 0 if coc.utils.get(clan.capital_districts, id=70000000) is None else coc.utils.get(clan.capital_districts, id=70000000).hall_level
        embed.add_field(name=f"{emoji}{clan.name} | CH{hall_level}",
                        value=f"> {bot.emoji.thick_sword} {raid.attack_count}/300 | "
                              f"{bot.emoji.person} {len(raid.members)}/50\n"
                              f"> {bot.emoji.capital_gold} {'{:,}'.format(raid.total_loot)} | "
                              f"{bot.emoji.raid_medal} {medals}", inline=False)

    return embed


async def create_wars(bot: CustomClient, guild: disnake.Guild, embed_color = disnake.Color.green()):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    if len(clan_tags) == 0:
        embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
        return embed

    war_list = await bot.get_clan_wars(tags=clan_tags)
    war_list = [w for w in war_list if w is not None and w.start_time is not None]
    if len(war_list) == 0:
        embed = disnake.Embed(description="No clans in war and/or have public war logs.", color=disnake.Color.red())
        return embed

    war_list = sorted(war_list, key=lambda l: (str(l.state), int(l.start_time.time.timestamp())), reverse=False)
    embed = disnake.Embed(description=f"**{guild.name} Current Wars**", color=embed_color)
    for war in war_list:
        if war.clan.name is None:
            continue
        emoji = await bot.create_new_badge_emoji(url=war.clan.badge.url)

        war_time = war.start_time.seconds_until
        if war_time < -172800:
            continue
        war_pos = "Starting"
        if war_time >= 0:
            war_time = war.start_time.time.replace(tzinfo=utc).timestamp()
        else:
            war_time = war.end_time.seconds_until
            if war_time <= 0:
                war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
                war_pos = "Ended"
            else:
                war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
                war_pos = "Ending"

        team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(7)
        opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)
        embed.add_field(name=f"{emoji}{war.clan.name} vs {war.opponent.name}",
                        value=f"> `{team_hits}`{bot.emoji.wood_swords}`{opp_hits}`\n"
                              f"> `{war.clan.stars:<7}`{bot.emoji.war_star}`{war.opponent.stars:>7}`\n"
                              f"> `{str(round(war.clan.destruction, 2)) + '%':<7}`<:broken_sword:944896241429540915>`{str(round(war.opponent.destruction, 2)) + '%':>7}`\n"
                              f"> {war_pos}: {bot.timestamper(int(war_time)).relative}", inline=False)

    embed.timestamp = datetime.now()
    return embed


async def create_trophies(bot: CustomClient, guild: disnake.Guild, sort_type: TrophySort):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    clans = await bot.get_clans(tags=clan_tags)
    clans = [clan for clan in clans if clan is not None]
    if not clans:
        return disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())

    if sort_type is TrophySort.home:
        point_type = "Trophies"
        clans = sorted(clans, key=lambda l: l.points, reverse=True)
        clan_text = [f"{bot.emoji.trophy}`{clan.points:5} {clan.name}`{create_superscript(clan.member_count)}" for clan in clans]
    elif sort_type is TrophySort.versus:
        point_type = "Versus Trophies"
        clans = sorted(clans, key=lambda l: l.builder_base_points, reverse=True)
        clan_text = [f"{bot.emoji.versus_trophy}`{clan.builder_base_points:5} {clan.name}`" for clan in clans]
    elif sort_type is TrophySort.capital:
        point_type = "Capital Trophies"
        clans = sorted(clans, key=lambda l: l.capital_points, reverse=True)
        clan_text = [f"{bot.emoji.capital_trophy}`{clan.capital_points:5} {clan.name}`" for clan in clans]

    clan_text = "\n".join(clan_text)

    embed = disnake.Embed(title=f"**{guild.name} {point_type}**", description=clan_text, color=disnake.Color.green())
    if guild.icon is not None:
        embed.set_footer(text="Last Refreshed", icon_url=guild.icon.url)
    embed.timestamp = datetime.now()
    return embed


async def create_summary(bot: CustomClient, guild: disnake.Guild, season:str):
    date = season
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})

    results = await bot.player_stats.find({"clan_tag": {"$in": clan_tags}}).to_list(length=2000)
    def gold(elem):
        g = elem.get("gold_looted")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return sum(g)
    top_gold = sorted(results, key=gold, reverse=True)[:10]


    text = f"**{bot.emoji.gold} Gold Looted\n**"
    for count, result in enumerate(top_gold, 1):
        try:
            looted_gold = sum(result['gold_looted'][date])
        except:
            looted_gold = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_gold):11} \u200e{result['name']}`\n"

    def elixir(elem):
        g = elem.get("elixir_looted")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return sum(g)
    top_elixir = sorted(results, key=elixir, reverse=True)[:10]

    text += f"**{bot.emoji.elixir} Elixir Looted\n**"
    for count, result in enumerate(top_elixir, 1):
        try:
            looted_elixir = sum(result['elixir_looted'][date])
        except:
            looted_elixir = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_elixir):11} \u200e{result['name']}`\n"

    def dark_elixir(elem):
        g = elem.get("dark_elixir_looted")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return sum(g)
    top_dark_elixir = sorted(results, key=dark_elixir, reverse=True)[:10]

    text += f"**{bot.emoji.dark_elixir} Dark Elixir Looted\n**"
    for count, result in enumerate(top_dark_elixir, 1):
        try:
            looted_dark_elixir = sum(result['dark_elixir_looted'][date])
        except:
            looted_dark_elixir = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(looted_dark_elixir):11} \u200e{result['name']}`\n"


    def activity_count(elem):
        g = elem.get("last_online_times")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return len(g)
    top_activity = sorted(results, key=activity_count, reverse=True)[:10]

    text += f"**{bot.emoji.clock} Top Activity\n**"
    for count, result in enumerate(top_activity, 1):
        try:
            activity = activity_count(result)
        except:
            activity = 0
        try:
            result['name']
        except:
            continue
        text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(activity):5} \u200e{result['name']}`\n"

    def donations(elem):
        g = elem.get("donations")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        g = g.get("donated")
        if g is None:
            return 0
        return g
    top_donations = sorted(results, key=donations, reverse=True)[:10]

    second_text = f"**{bot.emoji.up_green_arrow} Donations\n**"
    for count, result in enumerate(top_donations, 1):
        try:
            donated = result['donations'][date]['donated']
        except:
            donated = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(donated):7} \u200e{result['name']}`\n"

    def received(elem):
        g = elem.get("donations")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        g = g.get("received")
        if g is None:
            return 0
        return g
    top_received = sorted(results, key=received, reverse=True)[:10]

    second_text += f"**{bot.emoji.down_red_arrow} Received\n**"
    for count, result in enumerate(top_received, 1):
        try:
            received = result['donations'][date]['received']
        except:
            received = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(received):7} \u200e{result['name']}`\n"

    def attacks(elem):
        g = elem.get("attack_wins")
        if g is None:
            return 0
        g = g.get(date)
        if g is None:
            return 0
        return g
    top_attacks = sorted(results, key=attacks, reverse=True)[:10]

    second_text += f"**{bot.emoji.sword_clash} Attack Wins\n**"
    for count, result in enumerate(top_attacks, 1):
        try:
            attack_num = result['attack_wins'][date]
        except:
            attack_num = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(attack_num):7} \u200e{result['name']}`\n"


    def capital_gold_donated(elem):
        weeks = gen_raid_weekend_datestrings(4)
        weeks = weeks[0:4]
        cc_results = []
        for week in weeks:
            if elem is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            clan_capital_result = elem.get("capital_gold")
            if clan_capital_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            week_result = clan_capital_result.get(week)
            if week_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            cc_results.append(ClanCapitalWeek(week_result))
        return sum([sum(cap.donated) for cap in cc_results])

    top_cg_donos = sorted(results, key=capital_gold_donated, reverse=True)[:10]

    second_text += f"**{bot.emoji.capital_gold} CG Donated (last 4 weeks)\n**"
    for count, result in enumerate(top_cg_donos, 1):
        try:
            cg_donated = capital_gold_donated(result)
        except:
            cg_donated = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(cg_donated):7} \u200e{result['name']}`\n"


    def capital_gold_raided(elem):
        weeks = gen_raid_weekend_datestrings(4)
        weeks = weeks[0:4]
        cc_results = []
        for week in weeks:
            if elem is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            clan_capital_result = elem.get("capital_gold")
            if clan_capital_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            week_result = clan_capital_result.get(week)
            if week_result is None:
                cc_results.append(ClanCapitalWeek(None))
                continue
            cc_results.append(ClanCapitalWeek(week_result))
        return sum([sum(cap.raided) for cap in cc_results])

    top_cg_raided = sorted(results, key=capital_gold_raided, reverse=True)[:10]

    second_text += f"**{bot.emoji.capital_gold} CG Raided (last 4 weeks)\n**"
    for count, result in enumerate(top_cg_raided, 1):
        try:
            cg_raided = capital_gold_raided(result)
        except:
            cg_raided = 0
        try:
            result['name']
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(cg_raided):7} \u200e{result['name']}`\n"

    tags = [result.get("tag") for result in results]
    start = int(coc.utils.get_season_start().timestamp())
    now = (datetime.datetime.now().timestamp())
    hits = await bot.warhits.find(
        {"$and": [
            {"tag": {"$in" : tags}},
            {"_time": {"$gte": start}},
            {"_time": {"$lte": now}}
        ]}).to_list(length=100000)

    names = {}
    group_hits = defaultdict(int)
    for hit in hits:
        if hit["war_type"] == "friendly":
            continue
        group_hits[hit["tag"]]+= hit["stars"]
        names[hit["tag"]] = hit['name']

    top_war_stars = sorted(group_hits.items(), key=lambda x:x[1], reverse=True)[:10]

    second_text += f"**{bot.emoji.war_star} War Stars\n**"
    for count, result in enumerate(top_war_stars, 1):
        tag, war_star = result
        try:
            name = names[tag]
        except:
            continue
        second_text += f"{bot.get_number_emoji(color='blue', number=count)} `{'{:,}'.format(war_star):3} \u200e{name}`\n"

    embed = disnake.Embed(title=f"{guild.name} Season Summary", description=text)
    embed2 = disnake.Embed(description=second_text)
    print(len(embed.description) + len(embed2.description))
    return [embed, embed2]





async def create_joinhistory(bot: CustomClient, guild: disnake.Guild, season: str, embed_color = disnake.Color.green()):
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    text = ""

    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))

    pipeline = [
        {"$match": {"$and": [{"tag": {"$in": clan_tags}}, {"type": "members"},
                             {"time": {"$gte": season_start.timestamp()}},
                             {"time": {"$lte": season_end.timestamp()}}]}},
        {"$sort": {"tag": 1, "time": 1}},
        {"$group": {"_id": "$tag", "changes" : {"$push" : "$$ROOT"}}},
        {"$lookup": {"from": "clan_cache", "localField": "_id", "foreignField": "tag", "as": "name"}},
        {"$set": {"name": "$name.data.name"}}
    ]
    results: List[dict] = await bot.clan_history.aggregate(pipeline).to_list(length=None)

    class ItemHolder():
        def __init__(self, data):
            self.tag = data.get("tag")
            self.value = data.get("value")
            self.time = data.get("time")

    results = [r for r in results if r.get("name")]
    results.sort(key=lambda x: (x.get("name"))[0].upper())
    for clan in results:
        changes = clan.get("changes", [])
        name = clan.get("name")[0]
        if len(changes) <= 1:
            text += f"  0 Join   0 Left | {name[:13]}\n"

        joined = 0
        left = 0
        for count, change in enumerate(changes[1:]):
            previous_change = ItemHolder(data=changes[count])
            change = ItemHolder(data=change)
            if change.value - previous_change.value >= 0:
                joined += (change.value - previous_change.value)
            else:
                left += (previous_change.value - change.value)

        text += f"{joined:>4} J {left:>4} L {name[:13]}\n"

    embed = disnake.Embed(title=f"{guild.name} Join/Leave History", description=f"```{text}```", colour=embed_color)
    embed.set_footer(text="J = Join, L = Left")
    return embed