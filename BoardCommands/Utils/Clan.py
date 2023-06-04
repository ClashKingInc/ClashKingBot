import asyncio
import aiohttp
import coc
import emoji
import re
import disnake

from disnake import Embed, Color
from disnake.utils import get
from collections import defaultdict
from coc.raid import RaidLogEntry
from datetime import datetime
from CustomClasses.CustomPlayer import MyCustomPlayer, LegendRanking
from CustomClasses.CustomBot import CustomClient
from typing import List
from ballpark import ballpark as B
from statistics import mean
from utils.ClanCapital import gen_raid_weekend_datestrings, calc_raid_medals
from utils.clash import cwl_league_emojis, clan_super_troop_comp, clan_th_comp
from utils.discord_utils import fetch_emoji
from utils.general import create_superscript, response_to_line, fetch
from utils.constants import SUPER_SCRIPTS, MAX_NUM_SUPERS
from pytz import utc

async def clan_overview(bot: CustomClient, clan: coc.Clan, guild: disnake.Guild):
    db_clan = await bot.clan_db.find_one({"$and": [
        {"tag": clan.tag},
        {"server": guild.id}
    ]})

    clan_legend_ranking = await bot.clan_leaderboard_db.find_one(
        {"tag": clan.tag})

    previous_season = bot.gen_previous_season_date()
    season = bot.gen_season_date()

    clan_leader = get(clan.members, role=coc.Role.leader)
    warwin = clan.war_wins
    winstreak = clan.war_win_streak
    if clan.public_war_log:
        warloss = clan.war_losses
        if warloss == 0:
            winrate = warwin
        else:
            winrate = round((warwin / warloss), 2)
    else:
        warloss = "Hidden Log"
        winrate = "Hidden Log"

    if str(clan.location) == "International":
        flag = "<a:earth:861321402909327370>"
    else:
        try:
            flag = f":flag_{clan.location.country_code.lower()}:"
        except:
            flag = "ðŸ�³ï¸�"

    ranking = LegendRanking(clan_legend_ranking)
    rank_text = f"<a:earth:861321402909327370> {ranking.global_ranking} | "

    try:
        location_name = clan.location.name
    except:
        location_name = "Not Set"

    if clan.location is not None:
        if clan.location.name == "International":
            rank_text += f"ðŸŒ� {ranking.local_ranking}"
        else:
            rank_text += f"{flag} {ranking.local_ranking}"
    else:
        rank_text += f"{flag} {ranking.local_ranking}"
    if not str(ranking.local_ranking).isdigit() and not str(ranking.global_ranking).isdigit():
        rank_text = ""
    else:
        rank_text = f"Rankings: {rank_text}\n"

    cwl_league_emoji = cwl_league_emojis(str(clan.war_league))
    capital_league_emoji = cwl_league_emojis(str(clan.capital_league))

    hall_level = 0 if coc.utils.get(clan.capital_districts, id=70000000) is None else coc.utils.get(
        clan.capital_districts, id=70000000).hall_level
    hall_level_emoji = 1 if hall_level == 0 else hall_level
    clan_capital_text = f"Capital League: {capital_league_emoji}{clan.capital_league}\n" \
                        f"Capital Points: {bot.emoji.capital_trophy}{clan.capital_points}\n" \
                        f"Capital Hall: {fetch_emoji(f'Capital_Hall{hall_level_emoji}')} Level {hall_level}\n"

    clan_type_converter = {"open": "Anyone Can Join", "inviteOnly": "Invite Only", "closed": "Closed"}
    embed = Embed(
        title=f"**{clan.name}**",
        description=(
            f"Tag: [{clan.tag}]({clan.share_link})\n"
            f"Trophies: <:trophy:825563829705637889> {clan.points} | "
            f"<:vstrophy:944839518824058880> {clan.versus_points}\n"
            f"Requirements: <:trophy:825563829705637889>{clan.required_trophies} | {fetch_emoji(clan.required_townhall)}{clan.required_townhall}\n"
            f"Type: {clan_type_converter[clan.type]}\n"
            f"Location: {flag} {location_name}\n"
            f"{rank_text}\n"
            f"Leader: {clan_leader.name}\n"
            f"Level: {clan.level} \n"
            f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
            f"CWL: {cwl_league_emoji}{str(clan.war_league)}\n"
            f"Wars Won: <:warwon:932212939899949176>{warwin}\n"
            f"Wars Lost: <:warlost:932212154164183081>{warloss}\n"
            f"War Streak: <:warstreak:932212939983847464>{winstreak}\n"
            f"Winratio: <:winrate:932212939908337705>{winrate}\n\n"
            f"{clan_capital_text}\n"
            f"Description: {clan.description}"),
        color=Color.green()
    )

    player_tags = [member.tag for member in clan.members]
    clan_members: List[MyCustomPlayer] = await bot.get_players(tags=player_tags, custom=True)

    pipeline = [
        {"$match": {f"clan_games.{season}.clan" : clan.tag}},
        {"$group": {"_id": f"$clan_games.{season}.clan", "total_points": {"$sum": f"$clan_games.{season}.points"}}}
    ]
    clangames_season_stats = await bot.player_stats.aggregate(pipeline).to_list(length=None)
    if clangames_season_stats:
        clangames_season_stats = clangames_season_stats[0].get("total_points")
    if clangames_season_stats == 0 or not clangames_season_stats:
        pipeline = [
            {"$match": {f"clan_games.{previous_season}.clan": clan.tag}},
            {"$group": {"_id": f"$clan_games.{previous_season}.clan", "total_points": {"$sum": f"$clan_games.{previous_season}.points"}}}
        ]
        clangames_season_stats = await bot.player_stats.aggregate(pipeline).to_list(length=None)
        if clangames_season_stats:
            clangames_season_stats = clangames_season_stats[0].get("total_points")
        else:
            clangames_season_stats = 0
    cwl_text = "No Recent CWL\n"
    asyncio.create_task(bot.store_all_cwls(clan=clan))
    response = (await bot.cwl_db.find({"$and" : [{"clan_tag": clan.tag}, {"data" : {"$ne" : None}}]}).sort("season", -1).limit(1).to_list(length=1))
    if response and response[0].get("data") is not None:
        cwl_text, year = response_to_line(response[0].get("data"), clan)
        cwl_text = f"{cwl_text[:-2]} {year}`\n"

    raid_season_stats = await bot.player_stats.find({f"tag": {"$in": [member.tag for member in clan.members]}}).to_list(length=100)
    donated_cc = 0
    for date in gen_raid_weekend_datestrings(number_of_weeks=4):
        donated_cc += sum([sum(player.get(f"capital_gold").get(f"{date}").get("donate")) for player in raid_season_stats
                           if player.get("capital_gold") is not None and player.get("capital_gold").get(
                f"{date}") is not None and
                           player.get("capital_gold").get(f"{date}").get("donate") is not None])

    total_donated = sum([player.donos().donated for player in clan_members])
    total_received = sum([player.donos().received for player in clan_members])

    now = datetime.utcnow()
    time_add = defaultdict(set)
    for player in clan_members:
        for time in player.season_last_online():
            time_to_date = datetime.fromtimestamp(time)
            if now.date() == time_to_date.date():
                continue
            time_add[str(time_to_date.date())].add(player.tag)

    num_players_day = []
    for date, players in time_add.items():
        num_players_day.append(len(players))

    try:
        avg_players = int(sum(num_players_day) / len(num_players_day))
    except:
        avg_players = 0

    embed.add_field(name="Season Stats", value=f"Clan Games: {'{:,}'.format(clangames_season_stats)} Points\n"
                                               f"CWL: {cwl_text}"
                                               f"Cap Gold: {'{:,}'.format(donated_cc)} Donated\n"
                                               f"Donos: {bot.emoji.up_green_arrow}{'{:,}'.format(total_donated)}, {bot.emoji.down_red_arrow}{'{:,}'.format(total_received)}\n"
                                               f"Active Daily: {avg_players} players/avg")
    th_comp = clan_th_comp(clan_members=clan_members)
    super_troop_comp = clan_super_troop_comp(clan_members=clan_members)

    embed.add_field(name="**Townhall Composition:**",
                    value=th_comp, inline=False)
    embed.add_field(name="**Boosted Super Troops:**",
                    value=super_troop_comp, inline=False)

    embed.set_thumbnail(url=clan.badge.large)
    if db_clan is not None:
        ctg = db_clan.get("category")
        if ctg is not None:
            category = f"Category: {ctg} Clans"
            embed.set_footer(text=category)
    embed.timestamp = datetime.now()
    return embed


async def linked_players(bot: CustomClient, guild: disnake.Guild, clan: coc.Clan, player_links):
    embed_description = f"{bot.emoji.discord}`Name           ` **Discord**\n"
    embed_footer = None

    player_link_count = 0
    player_link_dict = dict(player_links)
    for player in clan.members:
        player_link = player_link_dict[f"{player.tag}"]
        # user not linked to player
        if player_link is None:
            continue

        name = bot.clean_string(player.name)[:14]
        if len(name) <= 2:
            name = player.name

        player_link_count += 1
        member = guild.get_member(player_link)
        # member not found in server
        if member is None:
            member = ""
            embed_footer = "Discord blank if linked but not on this server."

        embed_description += f'\u200e{bot.emoji.green_tick}`{name:14}` \u200e{member}\n'

    # no players were linked
    if player_link_count == 0:
        embed_description = "No players linked."

    embed = Embed(
        title=f"{clan.name}: {player_link_count}/{clan.member_count} linked",
        description=embed_description, color=Color.green())

    if embed_footer is not None:
        embed.set_footer(text=embed_footer)

    return embed


async def unlinked_players(bot: CustomClient, clan: coc.Clan, player_links):
    embed_description = f"{bot.emoji.discord}`Name           ` **Player Tag**\n"
    unlinked_player_count = 0
    player_link_dict = dict(player_links)
    for player in clan.members:
        player_link = player_link_dict[f"{player.tag}"]
        # linked player found
        if player_link is not None:
            continue
        name = bot.clean_string(player.name)[:14]
        if len(name) <= 2:
            name = player.name
        unlinked_player_count += 1
        embed_description += f'\u200e{bot.emoji.red_tick}`{name:14}` \u200e{player.tag}\n'

    if unlinked_player_count == 0:
        embed_description = "No players unlinked."

    embed = Embed(
        title=f"{clan.name}: {unlinked_player_count}/{clan.member_count} unlinked",
        description=embed_description,
        color=Color.green())
    embed.timestamp = datetime.now()
    return embed


def player_trophy_sort(bot: CustomClient,   clan: coc.Clan):
    embed_description = ""
    place_index = 0

    for player in clan.members:
        place_index += 1
        place_string = f"{place_index}."
        place_string = place_string.ljust(3)
        embed_description += (
            f"\u200e`{place_string}` \u200e<:a_cups:667119203744088094> "
            f"\u200e{player.trophies} - \u200e{player.name}\n")

    embed = Embed(
        title=f"{clan.name} Players - Sorted: Trophies",
        description=embed_description,
        color=Color.green())

    embed.set_footer(icon_url=clan.badge.large, text=clan.name)

    return embed


async def player_townhall_sort(bot: CustomClient,   clan: coc.Clan):
    ranking = []
    thcount = defaultdict(int)

    async for player in clan.get_detailed_members():
        th_emoji = fetch_emoji(player.town_hall)
        thcount[player.town_hall] += 1
        ranking.append(
            [player.town_hall, f"{th_emoji}\u200e{player.name}\n"])

    ranking = sorted(ranking, key=lambda l: l[0], reverse=True)
    ranking = "".join([i[1] for i in ranking])

    embed = Embed(
        title=f"{clan.name} Players - Sorted: Townhall",
        description=ranking,
        color=Color.green())
    embed.set_thumbnail(url=clan.badge.large)

    footer_text = "".join(f"Th{index}: {th} " for index, th in sorted(
        thcount.items(), reverse=True) if th != 0)
    embed.set_footer(text=footer_text)

    return embed


async def opt_status(bot: CustomClient, clan: coc.Clan, embed_color: disnake.Color = disnake.Color.green()):
    in_count = 0
    out_count = 0
    thcount = defaultdict(int)
    out_thcount = defaultdict(int)
    pipeline = [
        {"$match" : {"$and" : [{"tag": {"$in": [member.tag for member in clan.members]}}, {"type" : "warPreference"}]}},
        {"$group" : {"_id": "$tag", "last_change": {"$last": "$time"}}}
    ]
    results: List[dict] = await bot.player_history.aggregate(pipeline).to_list(length=None)
    member_stats = {result["_id"] : f"`<t:{result['last_change']}:R>" for result in results}

    players: List[MyCustomPlayer] = await bot.get_players(tags=[member.tag for member in clan.members], custom=True, use_cache=False, fake_results=True)
    players.sort(key=lambda x: (-x.town_hall, x.name), reverse=False)
    opted_in_text = ""
    opted_out_text = ""
    for player in players:
        war_opt_time = member_stats.get(player.tag, "N/A`")
        if player.war_opted_in:
            opted_in_text += f"<:opt_in:944905885367537685>{player.town_hall_cls.emoji}\u200e`{emoji.replace_emoji(player.name)[:15]:15}{war_opt_time}\n"
            thcount[player.town_hall] += 1
            in_count += 1
        else:
            opted_out_text += f"<:opt_out:944905931265810432>{player.town_hall_cls.emoji}\u200e`{emoji.replace_emoji(player.name)[:15]:15}{war_opt_time}\n"
            out_thcount[player.town_hall] += 1
            out_count += 1

    if opted_in_text == "":
        opted_in_text = "None"
    if opted_out_text == "":
        opted_out_text = "None"

    in_string = ", ".join(f"Th{index}: {th} " for index, th in sorted(thcount.items(), reverse=True) if th != 0)
    out_string = ", ".join(f"Th{index}: {th} " for index, th in sorted(out_thcount.items(), reverse=True) if th != 0)

    embed = Embed(title=f"**War Opt Statuses**",
                  description=f"**Players Opted In - {in_count}:**\n{opted_in_text}\n", color=embed_color)

    embed2 = Embed(description=f"**Players Opted Out - {out_count}:**\n{opted_out_text}\n", color=embed_color)

    embed.set_author(name=f"{clan.name}", icon_url=clan.badge.url)
    embed2.set_footer(text=f"In: {in_string}\nOut: {out_string}")
    embed2.timestamp = datetime.now()
    return [embed, embed2]


async def war_log(bot: CustomClient, clan: coc.Clan, limit=25):
    embed_description = ""
    wars_counted = 0
    war_log = await bot.coc_client.get_warlog(clan.tag, limit=limit)
    for war in war_log:
        if war.is_league_entry:
            continue
        clan_attack_count = war.clan.attacks_used

        if war.result == "win":
            status = "<:warwon:932212939899949176>"
            op_status = "Win"

        elif ((war.opponent.stars == war.clan.stars) and
              (war.clan.destruction == war.opponent.destruction)):
            status = "<:dash:933150462818021437>"
            op_status = "Draw"

        else:
            status = "<:warlost:932212154164183081>"
            op_status = "Loss"

        time = f"<t:{int(war.end_time.time.replace(tzinfo=utc).timestamp())}:R>"
        war: coc.ClanWarLogEntry

        try:
            total = war.team_size * war.attacks_per_member
            num_hit = SUPER_SCRIPTS[war.attacks_per_member]
        except:
            total = war.team_size
            num_hit = SUPER_SCRIPTS[1]

        embed_description += (
            f"{status}**{op_status} vs "
            f"\u200e{war.opponent.name}**\n"
            f"({war.team_size} vs {war.team_size}){num_hit} | {time}\n"
            f"{war.clan.stars} <:star:825571962699907152> {war.opponent.stars} | "
            f"{clan_attack_count}/{total} | {round(war.clan.destruction, 1)}% | "
            f"+{war.clan.exp_earned}xp\n")

        wars_counted += 1

    if wars_counted == 0:
        embed_description = "Empty War Log"

    embed = Embed(
        description=embed_description,
        color=Color.green())
    embed.set_author(icon_url=clan.badge.large, name=f"{clan.name} WarLog (last {wars_counted})")
    return embed


async def super_troop_list(bot: CustomClient, clan: coc.Clan):
    boosted = ""
    none_boosted = ""

    async for player in clan.get_detailed_members():
        text = ""
        if player.town_hall < 11:
            continue

        num_super_troops = 0
        for troop in player.troops:
            if troop.is_active:
                text = f"{fetch_emoji(troop.name)} {text}"
                num_super_troops += 1
            if num_super_troops == MAX_NUM_SUPERS:
                break

        if num_super_troops == 1:
            text = f"{bot.emoji.blank} {text}"

        if text == "":
            none_boosted += f"{player.name}\n"
        else:
            boosted += f"{text} {player.name}\n"

    if boosted == "":
        boosted = "None"

    embed = Embed(
        description=f"\n**Boosting:**\n{boosted}",
        color=Color.green())

    if none_boosted == "":
        none_boosted = "None"

    embed.set_author(name=f"{clan.name} Boosting Statuses", icon_url=clan.badge.url)
    embed.add_field(name="Not Boosting:", value=none_boosted)
    embed.set_footer(text="Last Refreshed")
    embed.timestamp = datetime.now()
    return embed


def clan_th_composition(bot: CustomClient,   clan: coc.Clan, member_list):
    th_count_dict = defaultdict(int)
    th_sum = 0

    for member in member_list:
        th = member.town_hall
        th_sum += th
        th_count_dict[th] += 1

    embed_description = ""
    for th_level, th_count in sorted(th_count_dict.items(), reverse=True):
        if (th_level) <= 9:
            th_emoji = fetch_emoji(th_level)
            embed_description += f"{th_emoji} `TH{th_level} ` : {th_count}\n"

        else:
            th_emoji = fetch_emoji(th_level)
            embed_description += f"{th_emoji} `TH{th_level}` : {th_count}\n"

    th_average = round((th_sum / clan.member_count), 2)

    embed = Embed(
        title=f"{clan.name} Townhall Composition",
        description=embed_description,
        color=Color.green())

    embed.set_thumbnail(url=clan.badge.large)
    embed.set_footer(text=(
        f"Average Th: {th_average}\n"
        f"Total: {clan.member_count} accounts"))

    return embed


async def clan_capital_overview(bot: CustomClient, clan: coc.Clan, raid_log_entry: RaidLogEntry):
    if raid_log_entry is None:
        return Embed(description="No Raid Weekend Entry Found. Donation info may be available.", color=disnake.Color.green())
    attack_count = 0
    for member in raid_log_entry.members:
        attack_count += member.attack_count
    embed = disnake.Embed(title=f"{clan.name} Raid Weekend Overview", color=disnake.Color.green())
    embed.set_footer(
        text=f"{str(raid_log_entry.start_time.time.date()).replace('-', '/')}-{str(raid_log_entry.end_time.time.date()).replace('-', '/')}",
        icon_url=clan.badge.url)
    embed.add_field(name="Overview",
                    value=f"- {bot.emoji.capital_gold}{'{:,}'.format(raid_log_entry.total_loot)} Looted\n"
                          f"- {bot.fetch_emoji('District_Hall5')}{raid_log_entry.destroyed_district_count} Districts Destroyed\n"
                          f"- {bot.emoji.thick_sword}{attack_count}/300 Attacks Complete\n"
                          f"- {bot.emoji.person}{len(raid_log_entry.members)}/50 Participants\n"
                          f"- Start {bot.timestamper(raid_log_entry.start_time.time.timestamp()).relative}, End {bot.timestamper(raid_log_entry.end_time.time.timestamp()).relative}\n",
                    inline=False)
    atk_stats_by_district = defaultdict(list)
    for clan in raid_log_entry.attack_log:
        for district in clan.districts:
            atk_stats_by_district[district.name].append(len(district.attacks))

    offense_district_stats = "```"
    for district, list_atks in atk_stats_by_district.items():
        offense_district_stats += f"{round(mean(list_atks), 2):4} {district}\n"
    offense_district_stats += "```"

    def_stats_by_district = defaultdict(list)
    for clan in raid_log_entry.defense_log:
        for district in clan.districts:
            def_stats_by_district[district.name].append(len(district.attacks))

    def_district_stats = "```"
    for district, list_atks in def_stats_by_district.items():
        def_district_stats += f"{round(mean(list_atks), 2):4} {district}\n"
    def_district_stats += "```"

    embed.add_field("Detailed Stats (Offense)",
                    value=f"- Avg Loot/Raid : {B(int(raid_log_entry.total_loot / len(raid_log_entry.attack_log)))}\n"
                          f"- Avg Loot/Player: {B(int(raid_log_entry.total_loot / len(raid_log_entry.members)))}\n"
                          f"- Avg Hits/Clan: {round(raid_log_entry.attack_count / len(raid_log_entry.attack_log), 2)}\n",
                    inline=False)
    embed.add_field(name="(Avg Atks By District, Off)", value=offense_district_stats)
    embed.add_field(name="(Avg Atks By District, Def)", value=def_district_stats)

    attack_summary_text = f"```a=atks, d=districts, l=loot\n"
    for clan in raid_log_entry.attack_log:
        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        attack_summary_text += f"- {clan.name[:12]:12} {clan.attack_count:2}a {clan.destroyed_district_count:1}d {B(sum([d.looted for d in clan.districts])):3}l\n"

    defense_summary_text = "```"
    for clan in raid_log_entry.defense_log:
        # badge = await self.bot.create_new_badge_emoji(url=clan.badge.url)
        defense_summary_text += f"- {clan.name[:12]:12} {clan.attack_count:2}a {clan.destroyed_district_count:1}d {B(sum([d.looted for d in clan.districts])):3}l\n"

    attack_summary_text += "```"
    defense_summary_text += "```"
    embed.add_field(name=f"Attack Summary", value=attack_summary_text, inline=False)
    embed.add_field(name="Defense Summary", value=defense_summary_text, inline=False)

    members = sorted(list(raid_log_entry.members), key=lambda x: x.capital_resources_looted, reverse=True)
    top_text = ""
    for count, member in enumerate(members[:3], 1):
        member: coc.raid.RaidMember
        count_conv = {1: "gold",
                      2: "white",
                      3: "blue"}
        top_text += f"{bot.get_number_emoji(color=count_conv[count], number=count)}{bot.clean_string(member.name)} {bot.emoji.capital_gold}{member.capital_resources_looted}{create_superscript(member.attack_count)}\n"
    embed.add_field(name="Top 3 Raiders", value=top_text, inline=False)
    return embed


async def clan_raid_weekend_donation_stats(bot: CustomClient, clan: coc.Clan, weekend: str):
    member_tags = [member.tag for member in clan.members]
    capital_raiders = await bot.player_stats.distinct("tag", filter={
        "$or": [{f"capital_gold.{weekend}.raided_clan": clan.tag}, {"tag": {"$in": member_tags}}]})
    players = await bot.get_players(tags=capital_raiders)

    donated_data = {}
    number_donated_data = {}
    donation_text = ""

    players.sort(key=lambda x: sum(x.clan_capital_stats(week=weekend).donated), reverse=True)
    for player in players:  # type: MyCustomPlayer
        sum_donated = 0
        len_donated = 0
        cc_stats = player.clan_capital_stats(week=weekend)
        sum_donated += sum(cc_stats.donated)
        len_donated += len(cc_stats.donated)

        donated_data[player.tag] = sum_donated
        number_donated_data[player.tag] = len_donated

        if player.tag in member_tags:
            donation_text += f"{bot.emoji.capital_gold}`{sum_donated:6} {player.clear_name[:15]:15}`\n"
        else:
            donation_text += f"{bot.emoji.deny_mark}`{sum_donated:6} {player.clear_name[:15]:15}`\n"

    donation_embed = Embed(
        title=f"**{clan.name} Donation Totals**",
        description=donation_text, color=Color.green())

    donation_embed.set_footer(text=f"Donated: {'{:,}'.format(sum(donated_data.values()))} | Week: {weekend}")
    return donation_embed


async def clan_raid_weekend_raid_stats(bot: CustomClient, clan: coc.Clan, raid_log_entry: RaidLogEntry):
    if raid_log_entry is None:
        embed = Embed(
            title=f"**{clan.name} Raid Totals**",
            description="No raid found! Donation info may be available.", color=Color.green())
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
        attack_limit[member.tag] += (
                member.attack_limit +
                member.bonus_attack_limit)
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
            raid_text.append([
                f"\u200e{bot.emoji.capital_gold}`"
                f"{total_attacks[tag]}/{attack_limit[tag]} "
                f"{amount:5} {name[:15]:15}`", amount])
        else:
            raid_text.append([
                f"\u200e{bot.emoji.deny_mark}`"
                f"{total_attacks[tag]}/{attack_limit[tag]} "
                f"{amount} {name[:15]:15}`", amount])

    more_to_show = 55 - len(total_attacks.values())
    for member in members_not_looted[:more_to_show]:
        member = coc.utils.get(clan.members, tag=member)
        name = bot.clean_string(member.name)
        raid_text.append([
            f"{bot.emoji.capital_gold}`{0}"
            f"/{6} {0:5} {name[:15]:15}`",
            0])

    raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
    raid_text = [line[0] for line in raid_text]
    raid_text = "\n".join(raid_text)

    raid_embed = Embed(
        title=f"**{clan.name} Raid Totals**",
        description=raid_text,
        color=Color.green())

    raid_embed.set_footer(text=(
        f"Spots: {len(total_attacks.values())}/50 | "
        f"Attacks: {sum(total_attacks.values())}/300 | "
        f"Looted: {'{:,}'.format(sum(total_looted.values()))} | {raid_log_entry.start_time.time.date()}"))

    return raid_embed


def create_last_online(bot: CustomClient,   clan: coc.Clan, clan_members):
    embed_description_list = []
    last_online_sum = 0
    last_online_count = 0
    for member in clan_members:
        if member.last_online is None:
            last_online_sort = 0
            embed_description_list.append([
                f"Not Seen `{member.name}`",
                last_online_sort])

        else:
            last_online_sort = member.last_online
            last_online_count += 1
            last_online_sum += member.last_online

            embed_description_list.append([
                f"<t:{member.last_online}:R> `{member.name}`",
                last_online_sort])

    embed_description = sorted(
        embed_description_list, key=lambda l: l[1], reverse=True)
    embed_description = [line[0] for line in embed_description]
    embed_description = "\n".join(embed_description)

    if last_online_sum != 0:
        avg_last_online = last_online_sum / last_online_count
        embed_description += (
            f"\n\n**Median L.O.** <t:{int(avg_last_online)}:R>")

    embed = Embed(
        title=f"**{clan.name} Last Online**",
        description=embed_description,
        color=Color.green())

    return embed


def create_activities(bot: CustomClient, clan: coc.Clan, clan_members, season):
    embed_description_list = []
    for member in clan_members:
        member: MyCustomPlayer
        last_online = member.season_last_online(season_date=season)
        name = member.name
        name = re.sub('[*_`~/]', '', name)
        name = name[:15]
        name = name.ljust(15)
        embed_description_list.append(
            [f"{str(len(last_online)).center(4)} | {name}", len(last_online)])

    embed_description_list_sorted = sorted(
        embed_description_list, key=lambda l: l[1], reverse=True)
    embed_description = [f"{bot.get_number_emoji(color='gold', number=count + 1)} `{line[0]}`" for count, line in
                         enumerate(embed_description_list_sorted)]
    embed_description = "\n".join(embed_description)

    embed = Embed(
        title=f"**{clan.name} Activity Count**",
        description=f"`    #     NAME         `\n{embed_description}",
        color=Color.green())
    embed.set_footer(text=f"{season} Season")
    return embed


def create_clan_games(bot: CustomClient,   clan: coc.Clan, player_list, member_tags, season_date):
    point_text_list = []
    total_points = sum(player.clan_games(season_date) for player in player_list)

    for player in player_list:
        player: MyCustomPlayer
        name = player.name
        for char in ["`", "*", "_", "~", "Â´"]:
            name = name.replace(char, "", len(player.name))

        points = player.clan_games(season_date)

        if player.tag in member_tags:
            point_text_list.append([
                f"{Emojis().clan_games}`{str(points).ljust(4)}` {name}",
                points])

        else:
            point_text_list.append([
                f"{Emojis().deny_mark}`{str(points).ljust(4)}` {name}",
                points])

    point_text_list_sorted = sorted(point_text_list, key=lambda l: l[1], reverse=True)

    point_text = [line[0] for line in point_text_list_sorted]
    point_text = "\n".join(point_text)

    cg_point_embed = Embed(
        title=f"**{clan.name} Clan Game Totals**",
        description=point_text,
        color=Color.green())

    cg_point_embed.set_footer(
        text=f"Total Points: {'{:,}'.format(total_points)}")

    return cg_point_embed


def clan_donations(bot: CustomClient,   clan: coc.Clan, type: str, season_date, player_list):
    donated_text = []
    received_text = []
    ratio_text = []
    total_donated = sum(
        player.donos(season_date).donated for player in player_list)

    total_received = sum(
        player.donos(season_date).received for player in player_list)

    for player in player_list:
        player: MyCustomPlayer
        name = player.name

        for char in ["`", "*", "_", "~", "Â´"]:
            name = name.replace(char, "", len(player.name))

        name = emoji.replace_emoji(name, "")
        name = name[:13]

        donated_text.append([(
            f"{str(player.donos(season_date).donated).ljust(5)}  "
            f"{str(player.donos(season_date).received).ljust(5)}  {name}"),
            player.donos(season_date).donated])

        received_text.append([(
            f"{str(player.donos(season_date).received).ljust(5)}  "
            f"{str(player.donos(season_date).donated).ljust(5)}  {name}"),
            player.donos(season_date).received])

        ratio_text.append([(
            f"{str(player.donation_ratio(season_date)).ljust(5)}  {name}"),
            player.donation_ratio(season_date)])

    if type == "donated":
        donated_text = sorted(
            donated_text, key=lambda l: l[1], reverse=True)
        donated_text = [f"{count:2} {line[0]}" for count, line in enumerate(donated_text, 1)]
        donated_text = "\n".join(donated_text)
        donated_text = " # DON    REC    Name\n" + donated_text

        donation_embed = Embed(
            title=f"**{clan.name} Donations**",
            description=f"```{donated_text}```",
            color=Color.green())

        donation_embed.set_footer(
            icon_url=clan.badge.url,
            text=(
                f"Donations: {'{:,}'.format(total_donated)} | "
                f"Received : {'{:,}'.format(total_received)} | {season_date}"))

        return donation_embed

    elif type == "received":
        received_text = sorted(
            received_text, key=lambda l: l[1], reverse=True)
        received_text = [f"{count:2} {line[0]}" for count, line in enumerate(received_text, 1)]
        received_text = "\n".join(received_text)
        received_text = " # REC    DON    Name\n" + received_text
        received_embed = Embed(
            title=f"**{clan.name} Received**",
            description=f"```{received_text}```",
            color=Color.green())

        received_embed.set_footer(
            icon_url=clan.badge.url,
            text=(
                f"Donations: {'{:,}'.format(total_donated)} | "
                f"Received : {'{:,}'.format(total_received)} | {season_date}"))
        return received_embed

    else:
        ratio_text = sorted(ratio_text, key=lambda l: l[1], reverse=True)
        ratio_text = [f"{count:2} {line[0]}" for count, line in enumerate(ratio_text, 1)]
        ratio_text = "\n".join(ratio_text)
        ratio_text = " # Ratio | Name\n" + ratio_text
        ratio_embed = Embed(
            title=f"**{clan.name} Ratios**", description=f"```{ratio_text}```",
            color=Color.green())

        ratio_embed.set_footer(
            icon_url=clan.badge.url,
            text=(
                f"Donations: {'{:,}'.format(total_donated)} | "
                f"Received : {'{:,}'.format(total_received)} | {season_date}"))

        return ratio_embed


def stat_components(bot: CustomClient):
    options = []
    for townhall in reversed(range(6, 16)):
        options.append(disnake.SelectOption(
            label=f"Townhall {townhall}", emoji=str(bot.fetch_emoji(name=townhall)), value=str(townhall)))
    th_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Townhalls",
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )
    options = []
    real_types = ["Fresh Hits", "Non-Fresh", "random", "cwl", "friendly"]
    for count, filter in enumerate(["Fresh Hits", "Non-Fresh", "Random Wars", "CWL", "Friendly Wars"]):
        options.append(disnake.SelectOption(
            label=f"{filter}", value=real_types[count]))
    filter_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Filters",
        min_values=1,  # the minimum number of options a user must select
        # the maximum number of options a user can select
        max_values=len(options),
    )
    options = []
    emojis = [bot.emoji.sword_clash.partial_emoji,
              bot.emoji.shield.partial_emoji, bot.emoji.war_star.partial_emoji]
    for count, type in enumerate(["Offensive Hitrate", "Defensive Rate", "Stars Leaderboard"]):
        options.append(disnake.SelectOption(
            label=f"{type}", emoji=emojis[count], value=type))
    stat_select = disnake.ui.Select(
        options=options,
        # the placeholder text to show when no options have been chosen
        placeholder="Select Stat Type",
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(th_select), disnake.ui.ActionRow(
        filter_select), disnake.ui.ActionRow(stat_select)]
    return dropdown

async def create_offensive_hitrate(bot: CustomClient, clan: coc.Clan, players,
                                   townhall_level: list = [], fresh_type: list = [False, True],
                                   start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                   war_types: list = ["random", "cwl", "friendly"],
                                   war_statuses=["lost", "losing", "winning", "won"]):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: MyCustomPlayer):
        hitrate = await player.hit_rate(townhall_level=townhall_level, fresh_type=fresh_type,
                                        start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                        war_types=war_types, war_statuses=war_statuses)
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        name = emoji.replace_emoji(player.name, "")
        name = str(name)[0:12]
        name = f"{name}".ljust(12)
        destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)
        return [f"{player.town_hall_cls.emoji}` {hr_nums} {destr} {name}`\n", round(hr.average_triples * 100, 3), name,
                hr.num_attacks, player.town_hall]

    for player in players:
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(
        ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
    text = "`# TH  NUM    HR%    NAME       `\n"
    for count, rank in enumerate(ranked, 1):
        spot_emoji = bot.get_number_emoji(color="gold", number=count)
        text += f"{spot_emoji}{rank[0]}"
    if len(ranked) == 0:
        text = "No War Attacks Tracked Yet."
    embed = disnake.Embed(title=f"Offensive Hit Rates",
                          description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append("Fresh")
    if False in fresh_type:
        filter_types.append("Non-Fresh")
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ", ".join(filter_types)
    time_range = "This Season"
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=clan.badge.url,
                     text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
    return embed


async def create_defensive_hitrate(bot: CustomClient, clan: coc.Clan, players,
                                   townhall_level: list = [], fresh_type: list = [False, True],
                                   start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                   war_types: list = ["random", "cwl", "friendly"],
                                   war_statuses=["lost", "losing", "winning", "won"]):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: MyCustomPlayer):
        hitrate = await player.defense_rate(townhall_level=townhall_level, fresh_type=fresh_type,
                                            start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                            war_types=war_types, war_statuses=war_statuses)
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
        name = emoji.replace_emoji(player.name, "")
        name = str(name)[0:12]
        name = f"{name}".ljust(12)
        destr = f"{round(hr.average_triples * 100, 1)}%".rjust(6)
        return [f"{player.town_hall_cls.emoji} `{hr_nums} {destr} {name}`\n", round(hr.average_triples * 100, 3), name,
                hr.num_attacks, player.town_hall]

    for player in players:  # type: MyCustomPlayer
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(
        ranked, key=lambda l: (-l[1], -l[-2], -l[-1], l[2]), reverse=False)
    text = "`# TH  NUM    DR%    NAME       `\n"
    for count, rank in enumerate(ranked, 1):
        spot_emoji = bot.get_number_emoji(color="gold", number=count)
        text += f"{spot_emoji}{rank[0]}"
    if len(ranked) == 0:
        text = "No War Attacks Tracked Yet."
    embed = disnake.Embed(title=f"Defensive Rates",
                          description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append("Fresh")
    if False in fresh_type:
        filter_types.append("Non-Fresh")
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ", ".join(filter_types)
    time_range = "This Season"
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=clan.badge.url,
                     text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
    return embed


async def create_stars_leaderboard(bot: CustomClient,   clan: coc.Clan, players,
                                   townhall_level: list = [], fresh_type: list = [False, True],
                                   start_timestamp: int = 0, end_timestamp: int = 9999999999,
                                   war_types: list = ["random", "cwl", "friendly"],
                                   war_statuses=["lost", "losing", "winning", "won"]):
    if not townhall_level:
        townhall_level = list(range(1, 17))
    tasks = []

    async def fetch_n_rank(player: MyCustomPlayer):
        hitrate = await player.hit_rate(townhall_level=townhall_level, fresh_type=fresh_type,
                                        start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                                        war_types=war_types, war_statuses=war_statuses)
        hr = hitrate[0]
        if hr.num_attacks == 0:
            return None
        name = str(player.name)[0:12]
        name = f"{name}".ljust(12)
        stars = f"{hr.total_stars}/{hr.num_attacks}".center(5)
        destruction = f"{int(hr.total_destruction)}%".ljust(5)
        return [f"{stars} {destruction} {name}\n", round(hr.average_triples * 100, 3), name, hr.total_stars,
                player.town_hall]

    for player in players:  # type: MyCustomPlayer
        task = asyncio.ensure_future(fetch_n_rank(player=player))
        tasks.append(task)
    responses = await asyncio.gather(*tasks)
    ranked = [response for response in responses if response is not None]
    ranked = sorted(
        ranked, key=lambda l: (-l[-2], -l[1], l[2]), reverse=False)
    text = "```#   â˜…     DSTR%  NAME       \n"
    for count, rank in enumerate(ranked, 1):
        # spot_emoji = self.bot.get_number_emoji(color="gold", number=count)
        count = f"{count}.".ljust(3)
        text += f"{count} {rank[0]}"
    text += "```"
    if len(ranked) == 0:
        text = "No War Attacks Tracked Yet."
    embed = disnake.Embed(title=f"Star Leaderboard",
                          description=text, colour=disnake.Color.green())
    filter_types = []
    if True in fresh_type:
        filter_types.append("Fresh")
    if False in fresh_type:
        filter_types.append("Non-Fresh")
    for type in war_types:
        filter_types.append(str(type).capitalize())
    filter_types = ", ".join(filter_types)
    time_range = "This Season"
    if start_timestamp != 0 and end_timestamp != 9999999999:
        time_range = f"{datetime.fromtimestamp(start_timestamp).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_timestamp).strftime('%m/%d/%y')}"
    embed.set_footer(icon_url=clan.badge.url,
                     text=f"{clan.name} | {time_range}\nFilters: {filter_types}")
    return embed


async def cwl_performance(bot: CustomClient, clan: coc.Clan):
    responses = await bot.cwl_db.find({"$and" : [{"clan_tag": clan.tag}, {"data" : {"$ne" : None}}]}).sort("season", -1).to_list(length=None)
    asyncio.create_task(bot.store_all_cwls(clan=clan))
    embed = Embed(
        title=f"**{clan.name} CWL History**",
        color=Color.green())

    embed.set_thumbnail(url=clan.badge.large)

    old_year = "2015"
    year_text = ""
    not_empty = False
    for response in responses:
        text, year = response_to_line(response.get("data"), clan)
        if year != old_year:
            if year_text != "":
                not_empty = True
                embed.add_field(
                    name=old_year,
                    value=year_text,
                    inline=False)

                year_text = ""
            old_year = year
        year_text += text

    if year_text != "":
        not_empty = True
        embed.add_field(
            name=f"**{old_year}**",
            value=year_text,
            inline=False)

    if not not_empty:
        embed.description = "No prior cwl data"

    return embed


async def simple_clan_embed(bot: CustomClient, clan: coc.Clan):
    leader = coc.utils.get(clan.members, role=coc.Role.leader)

    if clan.public_war_log:
        warwin = clan.war_wins
        warloss = clan.war_losses
        if warloss == 0:
            warloss = 1
        winstreak = clan.war_win_streak
        winrate = round((warwin / warloss), 2)
    else:
        warwin = clan.war_wins
        warloss = "Hidden Log"
        winstreak = clan.war_win_streak
        winrate = "Hidden Log"

    if str(clan.location) == "International":
        flag = "<a:earth:861321402909327370>"
    else:
        flag = f":flag_{clan.location.country_code.lower()}:"
    embed = disnake.Embed(title=f"**{clan.name}**",
                          description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                                      f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                                      f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                                      f"Location: {flag} {clan.location}\n\n"
                                      f"Leader: {leader.name}\n"
                                      f"Level: {clan.level} \n"
                                      f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                                      f"CWL: {cwl_league_emojis(str(clan.war_league))}{str(clan.war_league)}\n"
                                      f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                                      f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                                      f"Description: {clan.description}",
                          color=disnake.Color.green())

    embed.set_thumbnail(url=clan.badge.large)
    return embed