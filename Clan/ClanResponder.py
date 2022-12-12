import coc
from CustomClasses.CustomPlayer import LegendRanking
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
    get_raid
)
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.emoji_class import Emojis
from utils.clash import create_weekend_list, weekend_timestamps
import emoji
import math


async def clan_overview(
        clan: coc.Clan, db_clan, clan_legend_ranking):

    clan_leader = get(clan.members, role=coc.Role.leader)

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

    # getting the category of the clan set by server
    category = ""
    if db_clan is not None:
        ctg = db_clan.get("category")
        if ctg is not None:
            category = f"Category: {ctg}\n"

    if str(clan.location) == "International":
        flag = "<a:earth:861321402909327370>"
    else:
        try:
            flag = f":flag_{clan.location.country_code.lower()}:"
        except:
            flag = "🏳️"

    ranking = LegendRanking(clan_legend_ranking)

    rank_text = ""
    rank_text += f"<a:earth:861321402909327370> {ranking.global_ranking} | "

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

    cwl_league_emoji = league_and_trophies_emoji(str(clan.war_league))

    embed = Embed(
        title=f"**{clan.name}**",
        description=(
            f"Tag: [{clan.tag}]({clan.share_link})\n"
            f"Trophies: <:trophy:825563829705637889> {clan.points} | "
            f"<:vstrophy:944839518824058880> {clan.versus_points}\n"
            f"Required Trophies: <:trophy:825563829705637889> "
            f"{clan.required_trophies}\n"
            f"Required Townhall: {clan.required_townhall}\n"
            f"Location: {flag} {location_name}\n"
            f"Type: {clan.type}\n"
            f"{category}"
            f"Rankings: {rank_text}\n\n"
            f"Leader: {clan_leader.name}\n"
            f"Level: {clan.level} \n"
            f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
            f"CWL: {cwl_league_emoji} {str(clan.war_league)}\n"
            f"Wars Won: <:warwon:932212939899949176>{warwin}\n"
            f"Wars Lost: <:warlost:932212154164183081>{warloss}\n"
            f"War Streak: <:warstreak:932212939983847464>{winstreak}\n"
            f"Winratio: <:winrate:932212939908337705>{winrate}\n\n"
            f"Description: {clan.description}"),
        color=Color.green()
    )

    clan_members: list(coc.Player) = []
    async for player in clan.get_detailed_members():
        clan_members.append(player)

    th_comp = clan_th_comp(clan_members=clan_members)
    super_troop_comp = clan_super_troop_comp(clan_members=clan_members)

    embed.add_field(name="**Townhall Composition:**",
                    value=th_comp, inline=False)
    embed.add_field(name="**Boosted Super Troops:**",
                    value=super_troop_comp, inline=False)

    embed.set_thumbnail(url=clan.badge.large)

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
            member = member.mention

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


def clan_raid_weekend_stats(
        clan: coc.Clan, raid_log,
        capital_raid_members):
    weekend = "Current Week"

    choice_to_date = {
        "Current Week": [0],
        "Last Week": [1],
        "Last 4 Weeks (all)": [0, 1, 2, 3]
    }

    weekend_times = weekend_timestamps()
    weekend_dates = create_weekend_list(option=weekend)

    member_tags = [member.tag for member in clan.members]

    embeds = {}

    donated_data = {}
    number_donated_data = {}

    donation_text = []
    for player in capital_raid_members:
        if isinstance(player, coc.errors.NotFound):
            continue

        player: MyCustomPlayer

        for char in ["`", "*", "_", "~", "´", "`"]:
            name = player.name.replace(char, "")

        sum_donated = 0
        len_donated = 0

        for week in weekend_dates:
            cc_stats = player.clan_capital_stats(week=week)
            sum_donated += sum(cc_stats.donated)
            len_donated += len(cc_stats.donated)

        donation = f"{sum_donated}".ljust(6)

        donated_data[player.tag] = sum_donated
        number_donated_data[player.tag] = len_donated

        if sum_donated == 0 and len(weekend_dates) > 1:
            continue

        if player.tag in member_tags:
            donation_text.append(
                [f"{Emojis().capital_gold}`{donation}`: {name}",
                 sum_donated])

        else:
            donation_text.append(
                [f"{Emojis().deny_mark}`{donation}`: {name}",
                 sum_donated])

    donation_text = sorted(donation_text, key=lambda l: l[1], reverse=True)
    donation_text = [line[0] for line in donation_text]
    donation_text = "\n".join(donation_text)

    donation_embed = Embed(
        title=f"**{clan.name} Donation Totals**",
        description=donation_text, color=Color.green())

    donation_embed.set_footer(
        text=f"Donated: {'{:,}'.format(sum(donated_data.values()))}")

    embeds["donations"] = donation_embed

    raid_weekends = []
    for week in choice_to_date[weekend]:
        raid_weekend = get_raid(
            raid_log=raid_log, before=weekend_times[week],
            after=weekend_times[week + 1])
        if raid_weekend is not None:
            raid_weekends.append(raid_weekend)

    total_medals = 0
    if not raid_weekends:
        raid_embed = Embed(
            title=f"**{clan.name} Raid Totals**",
            description="No raids", color=Color.green())
        embeds["raids"] = raid_embed

        total_looted = None
        total_attacks = None
        donated_data = None
        number_donated_data = None

    else:
        total_attacks = defaultdict(int)
        total_looted = defaultdict(int)
        attack_limit = defaultdict(int)
        name_list = {}
        members_not_looted = member_tags.copy()
        for raid_weekend in raid_weekends:
            for member in raid_weekend.members:
                name_list[member.tag] = member.name
                total_attacks[member.tag] += member.attack_count
                total_looted[member.tag] += member.capital_resources_looted
                attack_limit[member.tag] += (
                    member.attack_limit +
                    member.bonus_attack_limit)

                if (len(raid_weekends) == 1 and
                        member.tag in members_not_looted):
                    members_not_looted.remove(member.tag)

        district_dict = {
            1: 135, 2: 225, 3: 350, 4: 405, 5: 460}
        capital_dict = {
            2: 180, 3: 360, 4: 585, 5: 810,
            6: 1115, 7: 1240, 8: 1260, 9: 1375, 10: 1450}

        attacks_done = sum(list(total_attacks.values()))
        raids = raid_weekends[0].attack_log
        for raid_clan in raids:
            for district in raid_clan.districts:
                if int(district.destruction) == 100:
                    if district.id == 70000000:
                        total_medals += capital_dict[int(
                            district.hall_level)]

                    else:
                        total_medals += district_dict[int(
                            district.hall_level)]

                else:
                    #attacks_done -= len(district.attacks)
                    pass

        print(total_medals)
        print(attacks_done)
        total_medals = math.ceil(total_medals/attacks_done) * 6

        raid_text = []
        for tag, amount in total_looted.items():
            raided_amount = f"{amount}".ljust(6)
            name = name_list[tag]
            for char in ["`", "*", "_", "~"]:
                name = name.replace(char, "", 10)
            # print(tag)
            # print(member_tags)
            if tag in member_tags:
                raid_text.append([(
                    f"\u200e{Emojis().capital_gold}`"
                    f"{total_attacks[tag]}/{attack_limit[tag]} "
                    f"{raided_amount}`: \u200e{name}", amount)])
            else:
                raid_text.append([(
                    f"\u200e{Emojis().deny_mark}`"
                    f"{total_attacks[tag]}/{attack_limit[tag]} "
                    f"{raided_amount}`: \u200e{name}", amount)])

        if len(raid_weekends) == 1:
            for member in members_not_looted:
                name = coc.utils.get(clan.members, tag=member)
                raid_text.append([(
                    f"{Emojis().capital_gold}`{0}"
                    f"/{6*len(raid_weekends)} {0}`: {name.name}"),
                    0])

        raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
        raid_text = [line[0] for line in raid_text]
        raid_text = "\n".join(raid_text)
        if len(raid_weekends) == 1:
            rw = raid_weekends[0]
            offensive_reward = rw.offensive_reward * 6
            if total_medals > offensive_reward:
                offensive_reward = total_medals

            defensive_reward = rw.defensive_reward
            raid_text += (
                f"\n\n{Emojis().raid_medal}{offensive_reward} + "
                f"{Emojis().raid_medal}{defensive_reward} = "
                f"{Emojis().raid_medal}"
                f"{offensive_reward + defensive_reward}"
                f"\n`Offense + Defense = Total`")

        raid_embed = Embed(
            title=f"**{clan.name} Raid Totals**",
            description=raid_text,
            color=Color.green())

        raid_embed.set_footer(text=(
            f"Spots: {len(total_attacks.values())}/50 | "
            f"Attacks: {sum(total_attacks.values())}/300 | "
            f"Looted: {'{:,}'.format(sum(total_looted.values()))}"))

        embeds["raids"] = raid_embed

    return (
        embeds, raid_weekends,
        total_looted, total_attacks, donated_data,
        number_donated_data)


async def clan_raid_weekend_raids(
        clan: coc.Clan, raid_log, weekend, client_emojis,
        partial_emoji_gen, create_new_badge_emoji):
    choice_to_date = {
        "Current Week": 0,
        "Last Week": 1,
        "2 Weeks Ago": 2}

    weekend_times = weekend_timestamps()

    embed = Embed(
        description=f"**{clan.name} Clan Capital Raids**",
        color=Color.green())

    raid_weekend = get_raid(
        raid_log=raid_log,
        before=weekend_times[choice_to_date[weekend]],
        after=weekend_times[choice_to_date[weekend] + 1])

    if raid_weekend is None:
        return (None, None)

    raids = raid_weekend.attack_log

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
                emoji = fetch_emoji(
                    name=f"Capital_Hall{district.hall_level}")

            else:
                emoji = fetch_emoji(
                    name=f"District_Hall{district.hall_level}")

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
