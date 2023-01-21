import asyncio
import aiohttp
import coc
from CustomClasses.CustomPlayer import LegendRanking
from CustomClasses.CustomBot import CustomClient
from disnake import Embed, Color, SelectOption
from disnake.utils import get
from utils.discord_utils import fetch_emoji
from collections import defaultdict
from Clan.ClanUtils import (
    SUPER_TROOPS,
    SUPER_SCRIPTS,
    clan_th_comp,
    clan_super_troop_comp,
    league_and_trophies_emoji,
    tiz,
    response_to_line
)
from utils.General import fetch
from coc.raid import RaidLogEntry
from datetime import datetime
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.emoji_class import Emojis
from CustomClasses.CustomBot import CustomClient
from utils.ClanCapital import gen_raid_weekend_datestrings, calc_raid_medals
from typing import List
import emoji
import math
import re
import disnake


async def clan_overview(clan: coc.Clan, db_clan, clan_legend_ranking, previous_season, season, bot: CustomClient):
    clan_leader = get(clan.members, role=coc.Role.leader)
    warwin = clan.war_wins
    winstreak = clan.war_win_streak
    if clan.public_war_log:
        warloss = clan.war_losses
        if warloss == 0:
            warloss = 1
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
            flag = "🏳️"

    ranking = LegendRanking(clan_legend_ranking)
    rank_text = f"<a:earth:861321402909327370> {ranking.global_ranking} | "

    try:
        location_name = clan.location.name
    except:
        location_name = "Not Set"

    if clan.location is not None:
        if clan.location.name == "International":
            rank_text += f"🌍 {ranking.local_ranking}"
        else:
            rank_text += f"{flag} {ranking.local_ranking}"
    else:
        rank_text += f"{flag} {ranking.local_ranking}"
    if not str(ranking.local_ranking).isdigit() and not str(ranking.global_ranking).isdigit():
        rank_text = ""
    else:
        rank_text = f"Rankings: {rank_text}\n"

    cwl_league_emoji = league_and_trophies_emoji(str(clan.war_league))
    capital_league_emoji = league_and_trophies_emoji(str(clan.capital_league))

    hall_level = 0 if coc.utils.get(clan.capital_districts, id=70000000) is None else coc.utils.get(clan.capital_districts, id=70000000).hall_level
    hall_level_emoji = 1 if hall_level == 0 else hall_level
    clan_capital_text = f"Capital League: {capital_league_emoji}{clan.capital_league}\n" \
                        f"Capital Points: {bot.emoji.capital_trophy}{clan.capital_points}\n" \
                        f"Capital Hall: {fetch_emoji(f'Capital_Hall{hall_level_emoji}')} Level {hall_level}\n"

    clan_type_converter = {"open" : "Anyone Can Join", "inviteOnly" : "Invite Only", "closed" : "Closed"}
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

    clangames_season_stats = await bot.player_stats.find({f"clan_games.{season}.clan" : clan.tag}).to_list(length=100)
    clangames_season_stats = sum([player.get(f"clan_games").get(f"{season}").get("points") for player in clangames_season_stats])
    if clangames_season_stats == 0:
        clangames_season_stats = await bot.player_stats.find({f"clan_games.{previous_season}.clan": clan.tag}).to_list(length=100)
        clangames_season_stats = sum([player.get(f"clan_games").get(f"{previous_season}").get("points") for player in clangames_season_stats])

    season_used = ""
    cwl_text = "No Recent CWL\n"
    response = await bot.cwl_db.find_one({"clan_tag" : clan.tag, "season" : season})
    if response is None:
        response = await bot.cwl_db.find_one({"clan_tag": clan.tag, "season": previous_season})
    if response is None:
        async with aiohttp.ClientSession() as session:
            url = (f"https://api.clashofstats.com/clans/{clan.tag.replace('#', '')}/cwl/seasons/{season}")
            season_used = season
            response = await fetch(url, session)
            if "Not Found" in str(response):
                url = (f"https://api.clashofstats.com/clans/{clan.tag.replace('#', '')}/cwl/seasons/{previous_season}")
                season_used = previous_season
                response = await fetch(url, session)
            await bot.cwl_db.insert_one({"clan_tag" : clan.tag,
                                     "season" : season_used,
                                     "data" : response})
    else:
        response = response.get("data")

    if "Not Found" not in str(response) and response is not None:
        text, year = response_to_line(response, clan)
        cwl_text = text

    raid_season_stats = await bot.player_stats.find({f"tag": {"$in" : [member.tag for member in clan.members]}}).to_list(length=100)
    donated_cc = 0
    for date in gen_raid_weekend_datestrings(number_of_weeks=4):
        donated_cc += sum([sum(player.get(f"capital_gold").get(f"{date}").get("donate")) for player in raid_season_stats
                                 if player.get("capital_gold") is not None and player.get("capital_gold").get(f"{date}") is not None and
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
        avg_players = int(sum(num_players_day)/len(num_players_day))
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
    return embed


def linked_players(server_members, clan: coc.Clan, player_links):

    green_check_emoji = "<:greentick:601900670823694357>"
    discord_emoji = "<:discord:840749695466864650>"

    embed_description = f"{discord_emoji}`Name           ` **Discord**\n"
    embed_footer = None

    player_link_count = 0

    player_link_dict = dict(player_links)

    for player in clan.members:
        player_link = player_link_dict[f"{player.tag}"]

        # user not linked to player
        if player_link is None:
            continue

        name = player.name

        ol_name = name
        for char in ["`", "*", "_", "~", "ッ"]:
            name = name.replace(char, "", 10)
        name = emoji.replace_emoji(name, "")
        name = name[:14]
        if len(name) <= 2:
            name = ol_name
        for x in range(14 - len(name)):
            name += " "

        player_link_count += 1

        member = get(server_members, id=player_link)

        # member not found in server
        if member == None:
            member = ""
            embed_footer = "Discord blank if linked but not on this server."
        else:
            member = str(member)

        embed_description += f'\u200e{green_check_emoji}`\u200e{name}` \u200e{member}'
        embed_description += "\n"

    # no players were linked
    if player_link_count == 0:
        embed_description = "No players linked."

    embed = Embed(
        title=f"{clan.name}: {player_link_count}/{clan.member_count} linked",
        description=embed_description, color=Color.green())

    if embed_footer is not None:
        embed.set_footer(text=embed_footer)

    return embed


def unlinked_players(clan: coc.Clan, player_links):

    red_x_emoji = "<:redtick:601900691312607242>"
    discord_emoji = "<:discord:840749695466864650>"

    embed_description = f"{discord_emoji}`Name           ` **Player Tag**\n"

    unlinked_player_count = 0

    player_link_dict = dict(player_links)

    for player in clan.members:
        player_link = player_link_dict[f"{player.tag}"]
        name = player.name

        # linked player found
        if player_link is not None:
            continue

        ol_name = name
        for char in ["`", "*", "_", "~", "ッ"]:
            name = name.replace(char, "", 10)
        name = emoji.replace_emoji(name, "")
        name = name[:14]
        if len(name) <= 2:
            name = ol_name
        for x in range(14 - len(name)):
            name += " "

        unlinked_player_count += 1
        member = player.tag

        embed_description += f'\u200e{red_x_emoji}`\u200e{name}` \u200e{member}'
        embed_description += "\n"

    if unlinked_player_count == 0:
        embed_description = "No players unlinked."

    embed = Embed(
        title=f"{clan.name}: {unlinked_player_count}/{clan.member_count} unlinked",
        description=embed_description,
        color=Color.green())

    return embed


def player_trophy_sort(clan: coc.Clan):
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


async def player_townhall_sort(clan: coc.Clan):
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


async def opt_status(clan: coc.Clan):
    opted_in = []
    opted_out = []
    in_count = 0
    out_count = 0
    thcount = defaultdict(int)
    out_thcount = defaultdict(int)

    async for player in clan.get_detailed_members():
        if player.war_opted_in:
            th_emoji = fetch_emoji(player.town_hall)
            opted_in.append(
                (player.town_hall, f"<:opt_in:944905885367537685>{th_emoji}"
                 f"\u200e{player.name}\n", player.name))
            thcount[player.town_hall] += 1
            in_count += 1

        else:
            th_emoji = fetch_emoji(player.town_hall)
            opted_out.append(
                (player.town_hall, f"<:opt_out:944905931265810432>{th_emoji}"
                 f"\u200e{player.name}\n", player.name))
            out_thcount[player.town_hall] += 1
            out_count += 1

    opted_in = sorted(opted_in, key=lambda opted_in_member: (
        opted_in_member[0], opted_in_member[2]), reverse=True)
    opted_in = "".join([i[1] for i in opted_in])

    opted_out = sorted(
        opted_out, key=lambda opted_out_member: (
            opted_out_member[0], opted_out_member[2]), reverse=True)
    opted_out = "".join([i[1] for i in opted_out])

    if not opted_in:
        opted_in = "None"
    if not opted_out:
        opted_out = "None"

    in_string = ", ".join(f"Th{index}: {th} " for index, th in sorted(
        thcount.items(), reverse=True) if th != 0)
    out_string = ", ".join(f"Th{index}: {th} " for index, th in sorted(
        out_thcount.items(), reverse=True) if th != 0)

    embed = Embed(
        title=f"**{clan.name} War Opt Statuses**",
        description=(
            f"**Players Opted In - {in_count}:**\n"
            f"{opted_in}\n"
            f"**Players Opted Out - {out_count}:**\n"
            f"{opted_out}\n"),
        color=Color.green())

    embed.set_thumbnail(url=clan.badge.large)
    embed.set_footer(
        text=(
            f"In: {in_string}\n"
            f"Out: {out_string}"))

    return embed


def war_log(clan: coc.Clan, war_log):

    embed_description = ""
    wars_counted = 0

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

        time = f"<t:{int(war.end_time.time.replace(tzinfo=tiz).timestamp())}:R>"
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
        title=f"**{clan.name} WarLog (last {wars_counted})**",
        description=embed_description,
        color=Color.green())
    embed.set_footer(icon_url=clan.badge.large, text=clan.name)
    return embed


async def super_troop_list(clan: coc.Clan):
    boosted = ""
    none_boosted = ""

    async for player in clan.get_detailed_members():
        troops = player.troop_cls
        troops = player.troops
        text = f"{player.name}"

        if player.town_hall < 11:
            continue

        num = 0

        for troop in troops:
            if troop.is_active:
                try:
                    if troop.name in SUPER_TROOPS:
                        text = f"{fetch_emoji(troop.name)} " + text

                        num += 1
                except:
                    pass

        if num == 1:
            text = "<:blanke:838574915095101470> " + text

        if text == player.name:
            none_boosted += f"{player.name}\n"

        else:
            boosted += f"{text}\n"

    if boosted == "":
        boosted = "None"

    embed = Embed(
        title=f"**{clan.name} Boosting Statuses**",
        description=f"\n**Boosting:**\n{boosted}",
        color=Color.green())

    embed.set_thumbnail(url=clan.badge.large)

    if none_boosted == "":
        none_boosted = "None"

    #embed.add_field(name="Boosting", value=boosted)
    embed.add_field(name="Not Boosting:", value=none_boosted)

    return embed


def clan_th_composition(clan: coc.Clan, member_list):
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


async def clan_raid_weekend_donation_stats(clan: coc.Clan, weekend: str, bot: CustomClient):

    member_tags = [member.tag for member in clan.members]
    capital_raid_member_tags = await bot.player_stats.distinct("tag", filter={f"capital_gold.{weekend}.raided_clan": clan.tag})
    all_tags = list(set(member_tags + capital_raid_member_tags))

    tasks = []
    for tag in all_tags:
        results = await bot.player_stats.find_one({"tag": tag})
        task = asyncio.ensure_future(
            bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=bot, results=results))
        tasks.append(task)
    capital_raid_members = await asyncio.gather(*tasks, return_exceptions=True)

    donated_data = {}
    number_donated_data = {}
    donation_text = []

    for player in capital_raid_members:
        if isinstance(player, coc.errors.NotFound):
            continue
        player: MyCustomPlayer
        name = re.sub('[*_`~/]', '', player.name)

        sum_donated = 0
        len_donated = 0
        cc_stats = player.clan_capital_stats(week=weekend)
        sum_donated += sum(cc_stats.donated)
        len_donated += len(cc_stats.donated)

        donation = f"{sum_donated}".ljust(6)

        donated_data[player.tag] = sum_donated
        number_donated_data[player.tag] = len_donated

        if player.tag in member_tags:
            donation_text.append(
                [f"{Emojis().capital_gold}`{donation}`: {name}", sum_donated])

        else:
            donation_text.append(
                [f"{Emojis().deny_mark}`{donation}`: {name}", sum_donated])

    donation_text = sorted(donation_text, key=lambda l: l[1], reverse=True)
    donation_text = [line[0] for line in donation_text]
    donation_text = "\n".join(donation_text)

    donation_embed = Embed(
        title=f"**{clan.name} Donation Totals**",
        description=donation_text, color=Color.green())

    donation_embed.set_footer(
        text=f"Donated: {'{:,}'.format(sum(donated_data.values()))}")
    return donation_embed


def clan_raid_weekend_raid_stats(clan: coc.Clan, raid_log_entry: RaidLogEntry):

    if raid_log_entry is None:
        embed = Embed(
            title=f"**{clan.name} Raid Totals**",
            description="No raid found!", color=Color.green())
        return (embed, None, None)

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
        raided_amount = f"{amount}".ljust(5)
        name = name_list[tag]
        name = re.sub('[*_`~/]', '', name)
        name= name[:13]
        if tag in member_tags:
            raid_text.append([
                f"\u200e{Emojis().capital_gold}`"
                f"{total_attacks[tag]}/{attack_limit[tag]} "
                f"{raided_amount}` \u200e{name}", amount])
        else:
            raid_text.append([
                f"\u200e{Emojis().deny_mark}`"
                f"{total_attacks[tag]}/{attack_limit[tag]} "
                f"{raided_amount}`\u200e{name}", amount])

    more_to_show =  55 - len(total_attacks.values())
    for member in members_not_looted[:more_to_show]:
        member = coc.utils.get(clan.members, tag=member)
        name = re.sub('[*_`~/]', '', member.name)
        raid_text.append([
            f"{Emojis().capital_gold}`{0}"
            f"/{6} {0}`: {name}",
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

    return (raid_embed, total_looted, total_attacks)


async def clan_raid_weekend_raids(
        clan: coc.Clan, raid_log_entry, client_emojis,
        partial_emoji_gen, create_new_badge_emoji):


    embed = Embed(
        description=f"**{clan.name} Clan Capital Raids**",
        color=Color.green())



    if raid_log_entry is None:
        return (None, None)

    raids = raid_log_entry.attack_log

    select_menu_options = [SelectOption(
        label="Overview",
        emoji=Emojis().sword_clash.partial_emoji,
        value="Overview")]

    embeds = {}

    total_attacks = 0
    total_looted = 0

    for raid_clan in raids:
        url = raid_clan.badge.url.replace(".png", "")
        emoji = get(
            client_emojis, name=url[-15:].replace("-", ""))

        if emoji is None:
            emoji = await create_new_badge_emoji(url=raid_clan.badge.url)
        else:
            emoji = f"<:{emoji.name}:{emoji.id}>"

        looted = sum(district.looted for district in raid_clan.districts)
        total_looted += looted
        total_attacks += raid_clan.attack_count

        embed.add_field(
            name=f"{emoji}\u200e{raid_clan.name}",
            value=(
                f"> {Emojis().sword} "
                f"Attacks: {raid_clan.attack_count}\n"
                f"> {Emojis().capital_gold} "
                f"Looted: {'{:,}'.format(looted)}"),
            inline=False)

        select_menu_options.append(SelectOption(
            label=raid_clan.name,
            emoji=partial_emoji_gen(emoji_string=emoji),
            value=raid_clan.tag))

        # create detailed embeds

        detail_embed = Embed(
            description=f"**Attacks on {raid_clan.name}**",
            color=Color.green())

        for district in raid_clan.districts:
            attack_text = ""
            for attack in district.attacks:
                attack_text += (
                    f"> \u200e{attack.destruction}% - "
                    f"\u200e{attack.attacker_name}\n")

            if district.id == 70000000:
                emoji = fetch_emoji(f"Capital_Hall{district.hall_level}")

            else:
                emoji = fetch_emoji(f"District_Hall{district.hall_level}")

            if attack_text == "":
                attack_text = "None"

            detail_embed.add_field(
                name=f"{emoji}{district.name}",
                value=attack_text, inline=False)

        embeds[raid_clan.tag] = detail_embed

    embed.set_footer(text=(
        f"Attacks: {total_attacks}/300 | "
        f"Looted: {'{:,}'.format(total_looted)}"))

    embeds["Overview"] = embed

    return (embeds, select_menu_options)


def create_last_online(clan: coc.Clan, clan_members):

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


def create_activities(bot, clan: coc.Clan, clan_members, season):
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
    embed_description = [f"{bot.get_number_emoji(color='gold', number=count + 1)} `{line[0]}`" for count, line in enumerate(embed_description_list_sorted)]
    embed_description = "\n".join(embed_description)

    embed = Embed(
        title=f"**{clan.name} Activity Count**",
        description=f"`    #     NAME         `\n{embed_description}",
        color=Color.green())
    embed.set_footer(text=f"{season} Season")
    return embed


def create_clan_games(
        clan: coc.Clan, player_list,
        member_tags, season_date):

    point_text_list = []
    total_points = sum(player.clan_games(season_date) for player in player_list)

    for player in player_list:
        player: MyCustomPlayer
        name = player.name
        for char in ["`", "*", "_", "~", "´"]:
            name = name.replace(char, "", len(player.name))

        points = player.clan_games(season_date)

        if player.tag in member_tags:
            point_text_list.append([
                f"{Emojis().clan_games}`{str(points).ljust(4)}`: {name}",
                points])

        else:
            point_text_list.append([
                f"{Emojis().deny_mark}`{str(points).ljust(4)}`: {name}",
                points])

    point_text_list_sorted = sorted(
        point_text_list, key=lambda l: l[1], reverse=True)

    point_text = [line[0] for line in point_text_list_sorted]
    point_text = "\n".join(point_text)

    cg_point_embed = Embed(
        title=f"**{clan.name} Clan Game Totals**",
        description=point_text,
        color=Color.green())

    cg_point_embed.set_footer(
        text=f"Total Points: {'{:,}'.format(total_points)}")

    return cg_point_embed


def clan_donations(clan: coc.Clan, type: str, season_date, player_list):

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

        for char in ["`", "*", "_", "~", "´"]:
            name = name.replace(char, "", len(player.name))

        name = emoji.replace_emoji(name, "")
        name = name[:13]

        donated_text.append([(
            f"{str(player.donos(season_date).donated).ljust(5)} | "
            f"{str(player.donos(season_date).received).ljust(5)} | {name}"),
            player.donos(season_date).donated])

        received_text.append([(
            f"{str(player.donos(season_date).received).ljust(5)} | "
            f"{str(player.donos(season_date).donated).ljust(5)} | {name}"),
            player.donos(season_date).received])

        ratio_text.append([(
            f"{str(player.donation_ratio(season_date)).ljust(5)} | {name}"),
            player.donation_ratio(season_date)])

    if type == "donated":
        donated_text = sorted(
            donated_text, key=lambda l: l[1], reverse=True)
        donated_text = [line[0] for line in donated_text]
        donated_text = "\n".join(donated_text)
        donated_text = "DON   | REC   | Name\n" + donated_text

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
        received_text = [line[0] for line in received_text]
        received_text = "\n".join(received_text)
        received_text = "REC   | DON   | Name\n" + received_text
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
        ratio_text = [line[0] for line in ratio_text]
        ratio_text = "\n".join(ratio_text)
        ratio_text = "Ratio | Name\n" + ratio_text
        ratio_embed = Embed(
            title=f"**{clan.name} Ratios**", description=f"```{ratio_text}```",
            color=Color.green())

        ratio_embed.set_footer(
            icon_url=clan.badge.url,
            text=(
                f"Donations: {'{:,}'.format(total_donated)} | "
                f"Received : {'{:,}'.format(total_received)} | {season_date}"))

        return ratio_embed


def stat_components(bot):
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


async def create_offensive_hitrate(bot, clan: coc.Clan, players,
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


async def create_defensive_hitrate(bot, clan: coc.Clan, players,
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


async def create_stars_leaderboard(clan: coc.Clan, players,
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
    text = "```#   ★     DSTR%  NAME       \n"
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


async def cwl_performance(clan: coc.Clan, dates):
    tasks = []
    async with aiohttp.ClientSession() as session:
        tag = clan.tag.replace("#", "")
        for date in dates:
            url = (
                f"https://api.clashofstats.com/clans/"
                f"{tag}/cwl/seasons/{date}")

            task = asyncio.ensure_future(fetch(url, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        await session.close()

    embed = Embed(
        title=f"**{clan.name} CWL History**",
        color=Color.green())

    embed.set_thumbnail(url=clan.badge.large)

    old_year = "2015"
    year_text = ""
    not_empty = False
    for response in responses:
        if "Not Found" in str(response):
            continue

        text, year = response_to_line(response, clan)

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
