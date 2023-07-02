import disnake
import coc
import operator
import re

from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from pytz import utc
from collections import defaultdict
from utils.general import create_superscript
from utils.clash import cwl_league_emojis, leagueAndTrophies
from utils.constants import war_leagues, leagues, SUPER_SCRIPTS
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.Misc import WarPlan
from typing import List

async def main_war_page(bot: CustomClient, war: coc.ClanWar, war_league=None):
    war_time = war.start_time.seconds_until
    war_state = "In Prep"
    war_pos = "Starting"
    if war_time >= 0:
        war_time = war.start_time.time.replace(tzinfo=utc).timestamp()
    else:
        war_time = war.end_time.seconds_until
        if war_time <= 0:
            war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
            war_pos = "Ended"
            war_state = "War Over"
        else:
            war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
            war_pos = "Ending"
            war_state = "In War"

    th_comps = await war_th_comps(bot=bot, war=war)

    if war_pos == "Ended":
        color = disnake.Color.red()
    elif war_pos == "Starting":
        color = disnake.Color.yellow()
    else:
        color = disnake.Color.green()



    embed = disnake.Embed(description=f"[**{war.clan.name}**]({war.clan.share_link})", color=color)
    embed.add_field(name=f"**War Against**", value=f"[**{war.opponent.name} ({war.clan_tag})**]({war.opponent.share_link})\n­\n",inline=False)


    state_text = f"{war_state} ({war.team_size} vs {war.team_size})\n" \
                 f"{war_pos}: <t:{int(war_time)}:R>\n­\n"
    if war.type == "cwl":
        state_text = f"{cwl_league_emojis(str(war_league))}{str(war_league)}\n" + state_text #clearer than equivalent f-string
    embed.add_field(name=f"**War State**", value=state_text, inline=False)


    team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(7)
    opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)
    embed.add_field(name="**War Stats**",
                    value=f"`{team_hits}`{bot.emoji.sword_clash}`{opp_hits}`\n"
                          f"`{war.clan.stars:<7}`<:star:825571962699907152>`{war.opponent.stars:>7}`\n"
                          f"`{str(round(war.clan.destruction, 2)) + '%':<7}`<:broken_sword:944896241429540915>`{str(round(war.opponent.destruction, 2)) + '%':>7}`"
                          f"\n­\n"
                    , inline=False)

    embed.add_field(name="War Composition", value=f"{war.clan.name}\n{th_comps[0]}\n"
                                                  f"{war.opponent.name}\n{th_comps[1]}", inline=False)

    if war.attacks:
        text = ""
        for attack in war.attacks[:5]:
            star_str = ""
            stars = attack.stars
            for x in range(0, stars):
                star_str += bot.emoji.war_star.emoji_string
            for x in range(0, 3 - stars):
                star_str += bot.emoji.no_star.emoji_string
            if attack.attacker.clan != war.clan:
                emoji = bot.emoji.shield
                name = attack.defender.name
            else:
                emoji = bot.emoji.sword
                name = attack.attacker.name
            destruction = f"{attack.destruction}".rjust(3)
            text += f"{emoji}`{destruction}%`{star_str}`{name}`\n"
        embed.add_field(name="­\nLast 5 attacks/defenses",
                        value=text)

    embed.timestamp = datetime.now()
    embed.set_thumbnail(url=war.clan.badge.large)
    embed.set_footer(text=f"{war.type.capitalize()} War")
    return embed


async def roster_embed(bot: CustomClient, war: coc.ClanWar):
    roster = ""
    tags = []
    lineup = []
    for player in war.members:
        if player not in war.opponent.members:
            tags.append(player.tag)
            lineup.append(player.map_position)

    x = 0
    async for player in bot.coc_client.get_players(tags):
        th = player.town_hall
        th_emoji = emojiDictionary(th)
        place = str(lineup[x]) + "."
        place = place.ljust(3)
        hero_total = 0
        hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
        heros = player.heroes
        for hero in heros:
            if hero.name in hero_names:
                hero_total += hero.level
        if hero_total == 0:
            hero_total = ""
        roster += f"`{place}` {th_emoji} {player.name} | {hero_total}\n"
        x += 1

    embed = disnake.Embed(title=f"{war.clan.name} War Roster", description=roster,
                          color=disnake.Color.green())
    embed.set_thumbnail(url=war.clan.badge.large)
    return embed


async def opp_roster_embed(bot: CustomClient, war):
    roster = ""
    tags = []
    lineup = []
    for player in war.opponent.members:
        tags.append(player.tag)
        lineup.append(player.map_position)

    x = 0
    async for player in bot.coc_client.get_players(tags):
        th = player.town_hall
        th_emoji = emojiDictionary(th)
        place = str(lineup[x]) + "."
        place = place.ljust(3)
        hero_total = 0
        hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
        heros = player.heroes
        for hero in heros:
            if hero.name in hero_names:
                hero_total += hero.level
        if hero_total == 0:
            hero_total = ""
        roster += f"`{place}` {th_emoji} {player.name} | {hero_total}\n"
        x += 1

    embed = disnake.Embed(title=f"{war.opponent.name} War Roster", description=roster,
                          color=disnake.Color.green())
    embed.set_thumbnail(url=war.opponent.badge.large)
    return embed


async def attacks_embed(bot: CustomClient, war: coc.ClanWar):
    attacks = ""
    missing_attacks = []
    for player in war.members:
        if player not in war.opponent.members:
            if player.attacks == []:
                missing_attacks.append(f"➼ {bot.fetch_emoji(name=player.town_hall)}{player.name}\n")
                continue
            name = player.name
            attacks += f"\n{bot.fetch_emoji(name=player.town_hall)}**{name}**"
            for a in player.attacks:
                star_str = ""
                stars = a.stars
                for x in range(0, stars):
                    star_str += "★"
                for x in range(0, 3 - stars):
                    star_str += "☆"

                base = create_superscript(a.defender.map_position)
                attacks += f"\n➼ {a.destruction}%{star_str}{base}"

    embed = disnake.Embed(title=f"{war.clan.name} War Attacks", description=attacks,
                          color=disnake.Color.green())
    if missing_attacks:
        split = [missing_attacks[i:i + 20] for i in range(0, len(missing_attacks), 20)]
        for item in split:
            embed.add_field(name="**No attacks done:**", value="".join(item), inline=False)
    embed.set_thumbnail(url=war.clan.badge.large)
    return embed


async def defenses_embed(bot: CustomClient, war: coc.ClanWar):
    defenses = ""
    missing_defenses = []
    for player in war.members:
        if player not in war.opponent.members:
            if player.defenses == []:
                missing_defenses.append(f"➼ {bot.fetch_emoji(name=player.town_hall)}{player.name}\n")
                continue
            name = player.name
            defenses += f"\n{bot.fetch_emoji(name=player.town_hall)}**{name}**"
            for a in player.defenses:
                star_str = ""
                stars = a.stars
                for x in range(0, stars):
                    star_str += "★"
                for x in range(0, 3 - stars):
                    star_str += "☆"

                base = await create_superscript(a.defender.map_position)
                defenses += f"\n➼ {a.destruction}%{star_str}{base}"

    embed = disnake.Embed(title=f"{war.clan.name} Defenses Taken", description=defenses,
                          color=disnake.Color.green())
    if missing_defenses:
        split = [missing_defenses[i:i + 20] for i in range(0, len(missing_defenses), 20)]
        for item in split:
            embed.add_field(name="**No defenses taken:**", value="".join(item))

    embed.set_thumbnail(url=war.clan.badge.large)
    return embed


async def opp_defenses_embed(bot: CustomClient, war: coc.ClanWar):
    defenses = ""
    missing_defenses = ""
    for player in war.opponent.members:
        name = player.name
        defense = f"**{name}**"
        if player.defenses == []:
            missing_defenses += f"➼ {player.name}\n"
            continue
        for d in player.defenses:
            if d == player.defenses[0]:
                defense += "\n➼ "
            if d != player.defenses[-1]:
                defense += f"{d.stars}★ {d.destruction}%, "
            else:
                defense += f"{d.stars}★ {d.destruction}%"

        defenses += f"{defense}\n"

    embed = disnake.Embed(title=f"{war.clan.name} Defenses Taken", description=defenses,
                          color=disnake.Color.green())
    if missing_defenses != "":
        embed.add_field(name="**No defenses taken:**", value=missing_defenses)
    embed.set_thumbnail(url=war.clan.badge.large)
    return embed


async def opp_overview(bot: CustomClient, war: coc.ClanWar):
    clan = await bot.getClan(war.opponent.tag)
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

    flag = ""
    if str(clan.location) == "International":
        flag = "<a:earth:861321402909327370>"
    else:
        flag = f":flag_{clan.location.country_code.lower()}:"
    embed = disnake.Embed(title=f"**War Opponent: {clan.name}**", description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                                                                              f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                                                                              f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                                                                              f"Location: {flag} {clan.location}\n\n"
                                                                              f"Leader: {leader.name}\n"
                                                                              f"Level: {clan.level} \n"
                                                                              f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                                                                              f"CWL: {leagueAndTrophies(str(clan.war_league))}{str(clan.war_league)}\n"
                                                                              f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                                                                              f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                                                                              f"Description: {clan.description}",
                          color=disnake.Color.green())

    embed.set_thumbnail(url=clan.badge.large)
    return embed


async def plan_embed(bot: CustomClient, plans, war: coc.ClanWar, embed_color = disnake.Color.green()) -> disnake.Embed:
    plans = [WarPlan(p) for p in plans]
    text = ""
    for plan in sorted(plans, key=lambda x: x.map_position):
        text += f"({plan.map_position}){bot.fetch_emoji(name=plan.townhall_level)}{plan.name} | {plan.plan_text}\n"

    if text == "":
        text = "No Plans Inserted Yet"
    embed = disnake.Embed(title=f"{war.clan.name} vs {war.opponent.name} WarPlan", description=text, colour=embed_color)
    return embed


async def create_components(bot: CustomClient, plans, war: coc.ClanWar):
    plans = [WarPlan(p) for p in plans]
    player_options = []
    player_options_two = []

    for count, player in enumerate(war.clan.members, 1):
        plan = coc.utils.get(plans, player_tag=player.tag)
        plan_done = "✅" if plan is not None else "❌"

        if count <= 25:
            player_options.append(disnake.SelectOption(label=f"({count}) {player.name} {plan_done}",
                                                       emoji=bot.fetch_emoji(
                                                           name=player.town_hall).partial_emoji,
                                                       value=f"lineup_{player.tag}"))
        else:
            player_options_two.append(disnake.SelectOption(label=f"({count}) {player.name} {plan_done}",
                                                           emoji=bot.fetch_emoji(
                                                               name=player.town_hall).partial_emoji,
                                                           value=f"lineup_{player.tag}"))

    player_select = disnake.ui.Select(
        options=player_options,
        placeholder=f"Set Plan for Players",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(player_options),  # the maximum number of options a user can select
    )
    if player_options_two:
        player_select_two = disnake.ui.Select(
            options=player_options_two,
            placeholder=f"Set Plan for Players #2",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=len(player_options_two),  # the maximum number of options a user can select
        )
        return [disnake.ui.ActionRow(player_select), disnake.ui.ActionRow(player_select_two)]
    return [disnake.ui.ActionRow(player_select)]


async def open_modal(bot: CustomClient, res: disnake.MessageInteraction):
    components = [
        disnake.ui.TextInput(
            label=f"Expected Stars",
            placeholder='can be a range like "1-2" or single like "2"',
            custom_id=f"stars",
            required=True,
            style=disnake.TextInputStyle.single_line,
            max_length=50,
        ),
        disnake.ui.TextInput(
            label=f"Enter the target(s)",
            placeholder='can be a range like "1-10" or single like "5"',
            custom_id=f"target",
            required=True,
            style=disnake.TextInputStyle.single_line,
            max_length=50,
        )
    ]
    custom_id = f"warplan-{int(datetime.now().timestamp())}"
    await res.response.send_modal(
        title="Enter Plan for Selected Players",
        custom_id=custom_id,
        components=components)

    def check(modal_res: disnake.ModalInteraction):
        return res.author.id == modal_res.author.id and custom_id == modal_res.custom_id

    modal_inter: disnake.ModalInteraction = await bot.wait_for(
        "modal_submit",
        check=check,
        timeout=300,
    )
    await modal_inter.send(content="Added.", ephemeral=True, delete_after=1)
    stars = modal_inter.text_values["stars"]
    target = modal_inter.text_values["target"]
    return (stars, target)


async def war_th_comps(bot: CustomClient, war: coc.ClanWar):
    thcount = defaultdict(int)
    opp_thcount = defaultdict(int)

    for player in war.clan.members:
        thcount[player.town_hall] += 1
    for player in war.opponent.members:
        opp_thcount[player.town_hall] += 1

    stats = ""
    for th_level, th_count in sorted(thcount.items(), reverse=True):
        th_emoji = bot.fetch_emoji(th_level)
        stats += f"{th_emoji}`{th_count}` "
    opp_stats = ""
    for th_level, th_count in sorted(opp_thcount.items(), reverse=True):
        th_emoji = bot.fetch_emoji(th_level)
        opp_stats += f"{th_emoji}`{th_count}` "

    return [stats, opp_stats]


async def calculate_potential_stars(num_ones, num_twos, num_threes, done_amount, total_left):
    if done_amount == 0:
        return 0
    ones = (num_ones / done_amount) * 1 * total_left
    twos = (num_twos / done_amount) * 2 * total_left
    threes = (num_threes / done_amount) * 3 * total_left
    return round(ones + twos + threes)


async def missed_hits(bot:CustomClient, war: coc.ClanWar):
    one_hit_missed = []
    two_hit_missed = []
    for player in war.clan.members:
        if len(player.attacks) < war.attacks_per_member:
            th_emoji = bot.fetch_emoji(name=player.town_hall)
            if war.attacks_per_member - len(player.attacks) == 1:
                one_hit_missed.append(f"{th_emoji}{player.name}")
            else:
                two_hit_missed.append(f"{th_emoji}{player.name}")

    embed = disnake.Embed(title=f"{war.clan.name} vs {war.opponent.name}",
                          description="Missed Hits", color=disnake.Color.orange())
    if one_hit_missed:
        embed.add_field(name="One Hit Missed", value="\n".join(one_hit_missed))
    if two_hit_missed:
        embed.add_field(name="Two Hits Missed", value="\n".join(two_hit_missed))
    embed.set_thumbnail(url=war.clan.badge.url)
    return embed


def get_latest_war(clan_league_wars: List[coc.ClanWar]):
    last_prep = None
    last_current = None
    for count, war in enumerate(clan_league_wars):
        if war.state == "preperation":
            last_prep = count
        elif war.state == "inWar":
            last_current = count
    if last_current is None:
        last_current = last_prep
    if last_current is None:
        last_current = len(clan_league_wars) - 1
    return last_current


def get_wars_at_round(clan_league_wars: List[coc.ClanWar], round: int):
    current_war = clan_league_wars[round]
    try:
        next_war = clan_league_wars[round + 1]
    except:
        next_war = None
    return (current_war, next_war)


async def get_cwl_wars(bot:CustomClient, clan: coc.Clan, season: str, group=None, fetched_clan=None):
    clan_league_wars = []
    clan_tag = clan.tag
    try:
        if group is None:
            group = await bot.coc_client.get_league_group(clan.tag)
        if group.season != season:
            raise Exception
        async for w in group.get_wars_for_clan(clan.tag):
            clan_league_wars.append(w)
        if clan_league_wars:
            return (group, clan_league_wars, None, clan.war_league)
    except:
        pass

    if not clan_league_wars:
        if fetched_clan is not None:
            clan_tag = fetched_clan
        response = await bot.cwl_db.find_one({"clan_tag": clan_tag, "season": season})
        if response is not None:
            group = coc.ClanWarLeagueGroup(data=response.get("data"), client=bot.coc_client)
            clan_league_wars = wars_from_group(bot=bot, data=response.get("data"), clan_tag=clan.tag, group=group)
            if clan_league_wars:
                league_name = [x["name"]for x in war_leagues["items"] if x["id"] == response.get("data").get("leagueId")][0]
                return (group, clan_league_wars, clan.tag, league_name)
        else:
            return (None, [], None, None)


async def star_lb(league_wars, clan, defense=False):
    star_dict = defaultdict(int)
    dest_dict = defaultdict(int)
    tag_to_name = defaultdict(str)
    num_attacks_done = defaultdict(int)
    num_wars_in = defaultdict(int)
    for war in league_wars:
        war: coc.ClanWar
        if str(war.state) == "preparation":
            continue
        for player in war.members:
            num_wars_in[player.tag] += 1
            tag_to_name[player.tag] = player.name
            if player not in war.opponent.members:
                if defense:
                    if player.defenses:
                        num_attacks_done[player.tag] += 1
                        defenses = player.defenses
                        top_defense = defenses[0]
                        for defense in defenses:
                            if defense.destruction > top_defense.destruction:
                                top_defense = defense
                        stars = top_defense.stars
                        destruction = top_defense.destruction
                        star_dict[player.tag] += stars
                        dest_dict[player.tag] += destruction
                else:
                    attacks = player.attacks
                    for attack in attacks:
                        num_attacks_done[player.tag] += 1
                        stars = attack.stars
                        destruction = attack.destruction
                        star_dict[player.tag] += stars
                        dest_dict[player.tag] += destruction

    star_list = []
    for tag, stars in star_dict.items():
        destruction = dest_dict[tag]
        name = tag_to_name[tag]
        hits_done = num_attacks_done[tag]
        num_wars = num_wars_in[tag]
        star_list.append([name, stars, destruction, f"{hits_done}/{num_wars}"])

    sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
    text = ""
    text += f"` # HIT ST DSTR NAME           `\n"
    x = 1
    for item in sorted_list:
        name = item[0]
        stars = str(item[1])
        dest = str(item[2])
        hits_done = item[3]
        rank = str(x)
        rank = rank.rjust(2)
        stars = stars.rjust(2)
        name = name.ljust(15)
        dest = dest.rjust(3) + "%"
        text += f"`\u200e{rank} {hits_done} {stars} {dest} \u200e{name}`\n"
        x+=1

    if defense:
        ty = "Defense"
    else:
        ty = "Offense"

    embed = disnake.Embed(title=f"{clan.name} {ty} Leaderboard", description=text,
                          color=disnake.Color.green())
    return embed


async def all_rounds(league_wars, clan):
    embed = disnake.Embed(title=f"{clan.name} CWL | All Rounds",
                          color=disnake.Color.green())

    r = 1
    for war in league_wars:
        war: coc.ClanWar
        war_time = war.start_time.seconds_until
        war_state = "In Prep"
        war_pos = "Starting"
        if war_time >= 0:
            war_time = war.start_time.time.replace(tzinfo=utc).timestamp()
        else:
            war_time = war.end_time.seconds_until
            if war_time <= 0:
                war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
                war_pos = "Ended"
                war_state = "War Over | "
            else:
                war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
                war_pos = "Ending"
                war_state = "In War |"
        team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(
            7)
        opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)
        emoji=""
        if str(war.status) == "won":
            emoji = "<:greentick:601900670823694357>"
        elif str(war.status) == "lost":
            emoji = "<:redtick:601900691312607242>"
        embed.add_field(name=f"**{war.clan.name}** vs **{war.opponent.name}**\n"
                             f"{emoji}Round {r} | {war_state} {str(war.status).capitalize()}",
                        value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                              f"`{war.clan.stars:<7}`<:star:825571962699907152>`{war.opponent.stars:7}`\n"
                              f"`{round(war.clan.destruction,2):<6}%`<:broken_sword:944896241429540915>`{round(war.opponent.destruction,2):6}%`\n"
                              f"{war_pos} <t:{int(war_time)}:R>\n­\n"
                        , inline=False)
        r+=1
    return embed


async def ranking_lb(bot: CustomClient, group: coc.ClanWarLeagueGroup, fetched_clan: str = None):
    star_dict = defaultdict(int)
    dest_dict = defaultdict(int)
    tag_to_name = defaultdict(str)

    league_wars = []
    if fetched_clan is not None:
        data = (await bot.cwl_db.find_one({"clan_tag": fetched_clan, "season": group.season})).get("data")
        league_wars = wars_from_group(bot=bot, group=group, data=data)
    rounds = group.rounds
    for round in rounds:
        for war_tag in round:
            if not league_wars:
                war = await bot.coc_client.get_league_war(war_tag)
            else:
                war = get_league_war_by_tag(league_wars=league_wars, war_tag=war_tag)
            if str(war.status) == "won":
                star_dict[war.clan.tag] += 10
            elif str(war.status) == "lost":
                star_dict[war.opponent.tag] += 10
            tag_to_name[war.clan.tag] = war.clan.name
            tag_to_name[war.opponent.tag] = war.opponent.name
            for player in war.members:
                attacks = player.attacks
                for attack in attacks:
                    star_dict[player.clan.tag] += attack.stars
                    dest_dict[player.clan.tag] += attack.destruction

    star_list = []
    for tag, stars in star_dict.items():
        destruction = dest_dict[tag]
        name = tag_to_name[tag]
        star_list.append([name, stars, destruction])

    sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
    text = ""
    text += f"`# STR DSTR   NAME           `"
    x = 1
    for item in sorted_list:
        name = item[0]
        stars = str(item[1])
        dest = str(item[2])
        rank = str(x)
        rank = rank.rjust(1)
        stars = stars.rjust(2)
        name = name.ljust(15)
        dest = dest.rjust(5) + "%"
        text += f"\n`\u200e{rank} \u200e{stars} {dest} \u200e{name}`"
        x += 1

    embed = disnake.Embed(title=f"Clan Ranking Leaderboard", description=text,
                          color=disnake.Color.green())
    return embed


async def all_members(bot: CustomClient, group:coc.ClanWarLeagueGroup, clan: coc.Clan):
    roster = ""
    our_clan = coc.utils.get(group.clans, tag=clan.tag)
    members = our_clan.members
    tags = [member.tag for member in members]

    x = 1
    for player in await bot.get_players(tags):
        if player is None:
            continue
        th = player.town_hall
        th_emoji = emojiDictionary(th)
        place = str(x) + "."
        place = place.ljust(3)
        hero_total = 0
        hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
        heros = player.heroes
        for hero in heros:
            if hero.name in hero_names:
                hero_total += hero.level
        if hero_total == 0:
            hero_total = ""
        name = re.sub('[*_`~/]', '', player.name)
        roster += f"\u200e`{place}` {th_emoji} \u200e{name}\u200e | {hero_total}\n"
        x += 1

    embed = disnake.Embed(title=f"{clan.name} CWL Members", description=roster,
                          color=disnake.Color.green())
    embed.set_thumbnail(url=clan.badge.large)
    return embed



async def page_manager(bot:CustomClient, page:str, group: coc.ClanWarLeagueGroup, war: coc.ClanWar, next_war: coc.ClanWar,
                       league_wars: List[coc.ClanWar], clan: coc.Clan, fetched_clan: str, war_league: str):
    if page == "cwlround_overview":
        embed = await main_war_page(bot=bot, war=war, war_league=war_league)
        return [embed]
    elif page == "round":
        embed = await main_war_page(bot=bot, war=war, war_league=war_league)
        return [embed]
    elif page == "nextround":
        embed = await main_war_page(bot=bot, war=next_war, war_league=war_league)
        return [embed]
    elif page == "lineup":
        embed1 = await roster_embed(bot=bot, war=next_war)
        embed2 = await opp_roster_embed(bot=bot, war=next_war)
        return[embed1, embed2]
    elif page == "stars":
        embed = await star_lb(league_wars, clan)
        embed2 = await star_lb(league_wars, clan, defense=True)
        return[embed, embed2]
    elif page == "rankings":
        embed = await ranking_lb(bot=bot, group=group, fetched_clan=fetched_clan)
        return [embed]
    elif page == "allrounds":
        embed = await all_rounds(league_wars, clan)
        return [embed]
    elif page == "all_members":
        embed = await all_members(bot=bot, group=group, clan=clan)
        return [embed]
    elif page == "current_lineup":
        embed1 = await roster_embed(bot=bot, war=war)
        embed2 = await opp_roster_embed(bot=bot, war=war)
        return [embed1, embed2]
    elif page == "attacks":
        embed = await attacks_embed(bot=bot, war=war)
        return [embed]
    elif page == "defenses":
        embed = await defenses_embed(bot=bot, war=war)
        return [embed]
    elif page == "nextopp_overview":
        embed = await opp_overview(bot=bot, war=war)
        return [embed]
    elif page == "missedhits":
        embed = await missed_hits(bot=bot, war=war)
        return [embed]


async def component_handler(bot: CustomClient, page: str, current_war: coc.ClanWar, next_war: coc.ClanWar, group: coc.ClanWarLeagueGroup, league_wars: List[coc.ClanWar], fetched_clan):
    round_stat_dropdown = await stat_components(bot=bot, war=current_war, next_war=next_war)
    overall_stat_dropdown = await overall_stat_components(bot=bot)
    clan_dropdown = await clan_components(group=group)
    round_dropdown = await round_components(league_wars=league_wars)
    r = None
    if "cwlround_" in page:
        round = page.split("_")[-1]
        if round == "overview":
            r = [overall_stat_dropdown, round_dropdown, clan_dropdown]
    elif page in ["stars", "rankings", "allrounds", "all_members", "excel", "missedhits"]:
        r =  [overall_stat_dropdown, round_dropdown, clan_dropdown]
    else:
        r =  [round_stat_dropdown, round_dropdown, clan_dropdown]
    if fetched_clan is not None:
        r = r[:-1]
    return r


async def overall_stat_components(bot:CustomClient):
    map = bot.partial_emoji_gen("<:map:944913638500761600>")
    star = bot.partial_emoji_gen("<:star:825571962699907152>")
    up = bot.partial_emoji_gen("<:warwon:932212939899949176>")

    options = [  # the options in your dropdown
        disnake.SelectOption(label="Star Leaderboard", emoji=star, value="stars"),
        disnake.SelectOption(label="Clan Rankings", emoji=up, value="rankings"),
        disnake.SelectOption(label="Missed Hits", emoji=bot.emoji.no.partial_emoji, value="missedhits"),
        disnake.SelectOption(label="All Rounds", emoji=map, value="allrounds"),
        disnake.SelectOption(label="All Members", emoji=bot.emoji.alphabet.partial_emoji, value="all_members"),
        disnake.SelectOption(label="Excel Export", emoji=bot.emoji.excel.partial_emoji, value="excel")
    ]

    select = disnake.ui.Select(
        options=options,
        placeholder="Overview Pages",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    return disnake.ui.ActionRow(select)


async def stat_components(bot:CustomClient, war: coc.ClanWar, next_war: coc.ClanWar):
    swords = bot.partial_emoji_gen("<a:swords:944894455633297418>", animated=True)
    troop = bot.partial_emoji_gen("<:troop:861797310224400434>")
    options = []

    # on first round - only next round
    # on last round - only current round
    if war is None:
        options.insert(0, disnake.SelectOption(label="Next Round", emoji=bot.emoji.right_green_arrow.partial_emoji, value="nextround"))
        options.insert(1, disnake.SelectOption(label="Next Round Lineup", emoji=troop, value="lineup"))
    elif next_war is None:
        options.insert(0, disnake.SelectOption(label="Current Round", emoji=swords, value="round"))
        options.insert(1, disnake.SelectOption(label="Current Lineup", emoji=troop, value="current_lineup"))
        options.insert(2, disnake.SelectOption(label="Attacks", emoji=bot.emoji.thick_sword.partial_emoji, value="attacks"))
        options.insert(3, disnake.SelectOption(label="Defenses", emoji=bot.emoji.shield.partial_emoji, value="defenses"))
    else:
        options.insert(0, disnake.SelectOption(label="Current Round", emoji=swords, value="round"))
        options.insert(1, disnake.SelectOption(label="Current Lineup", emoji=troop, value="current_lineup"))
        options.insert(2, disnake.SelectOption(label="Attacks", emoji=bot.emoji.thick_sword.partial_emoji,value="attacks"))
        options.insert(3, disnake.SelectOption(label="Defenses", emoji=bot.emoji.shield.partial_emoji,value="defenses"))

        options.insert(4, disnake.SelectOption(label="Next Round", emoji=bot.emoji.right_green_arrow.partial_emoji, value="nextround"))
        options.insert(5, disnake.SelectOption(label="Next Round Lineup", emoji=troop, value="lineup"))
        options.insert(6, disnake.SelectOption(label="Next Opponent Overview", emoji=bot.emoji.magnify_glass.partial_emoji, value="nextopp_overview"))

    select = disnake.ui.Select(
        options=options,
        placeholder="Round Stat Pages",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    return disnake.ui.ActionRow(select)


async def round_components(league_wars: List[coc.ClanWar]):
    options = [disnake.SelectOption(label=f"Overview", value=f"cwlround_overview")]
    for round in range(1, len(league_wars) + 1):
        options.append(disnake.SelectOption(label=f"Round {round}", value=f"cwlround_{round}"))

    select = disnake.ui.Select(
        options=options,
        placeholder="Choose a round",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    return disnake.ui.ActionRow(select)


async def clan_components(group: coc.ClanWarLeagueGroup):
    options = []
    for clan in group.clans:
        options.append(
            disnake.SelectOption(label=f"{clan.name}", value=f"cwlchoose_{clan.tag}"))

    select = disnake.ui.Select(
        options=options,
        placeholder="Choose a clan",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1,  # the maximum number of options a user can select
    )
    return disnake.ui.ActionRow(select)


def wars_from_group(bot:CustomClient, group: coc.ClanWarLeagueGroup, data: dict, clan_tag=None):
    rounds = data.get("rounds")
    list_wars = []
    for round in rounds:
        for war in round.get("wars"):
            if clan_tag is None or war.get("clan").get("tag") == clan_tag or war.get("opponent").get("tag") == clan_tag:
                #print(war["endTime"])
                war["endTime"] = datetime.fromtimestamp(war["endTime"]/1000).strftime('%Y%m%dT%H%M%S.000Z')
                war["startTime"] = datetime.fromtimestamp(war["startTime"]/1000).strftime('%Y%m%dT%H%M%S.000Z')
                war["preparationStartTime"] = datetime.fromtimestamp(war["preparationStartTime"]/1000).strftime('%Y%m%dT%H%M%S.000Z')
                for member in (war.get("clan").get("members") + war.get("opponent").get("members")):
                    if member.get("bestOpponentAttack") is None:
                        member["bestOpponentAttack"] = {}
                    member["townhallLevel"] = member["townHallLevel"]
                    if member.get("mapPosition") is None:
                        member["mapPosition"] = 1
                    if member.get("attack"):
                        attack = member.get("attack")
                        attack["duration"] = 0
                        member["attacks"] = [attack]
                list_wars.append(coc.ClanWar(data=war, clan_tag=clan_tag, client=bot.coc_client, league_group=group))
    return list_wars


def get_league_war_by_tag(league_wars: List[coc.ClanWar], war_tag: str):
    for war in league_wars:
        if war.war_tag == war_tag:
            return war


async def create_cwl_status(bot:CustomClient, guild: disnake.Guild):
    now = datetime.now()
    season = bot.gen_season_date()
    clan_tags = await bot.clan_db.distinct("tag", filter={"server": guild.id})
    if len(clan_tags) == 0:
        embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
        return embed

    clans = await bot.get_clans(tags=clan_tags)

    spin_list = []
    for clan in clans:
        if clan is None:
            continue
        c = [clan.name, clan.war_league.name, clan.tag]
        try:
            league = await bot.coc_client.get_league_group(clan.tag)
            state = league.state
            if str(state) == "preparation":
                c.append("<a:CheckAccept:992611802561134662>")
                c.append(1)
            elif str(state) == "ended":
                c.append("<:dash:933150462818021437>")
                c.append(3)
            elif str(state) == "inWar":
                c.append("<a:swords:944894455633297418>")
                c.append(0)
            elif str(state) == "notInWar":
                c.append("<a:spinning:992612297048588338>")
                c.append(2)
        except coc.NotFound:
            c.append("<:dash:933150462818021437>")
            c.append(3)
        spin_list.append(c)

    clans_list = sorted(spin_list, key=lambda x: (x[1], x[4]), reverse=False)

    main_embed = disnake.Embed(title=f"__**{guild.name} CWL Status**__",
                               color=disnake.Color.green())

    #name, league, clan, status emoji, order
    for league in leagues:
        text = ""
        for clan in clans_list:
            if clan[1] == league:
                text += f"{clan[3]} {clan[0]}\n"
            if (clan[2] == clans_list[len(clans_list) - 1][2]) and (text != ""):
                main_embed.add_field(name=f"**{league}**", value=text, inline=False)

    main_embed.add_field(name="Legend", value=f"<a:spinning:992612297048588338> Spinning | <:dash:933150462818021437> Not Spun | <a:CheckAccept:992611802561134662> Prep |  <a:swords:944894455633297418> War")
    main_embed.timestamp = now
    main_embed.set_footer(text="Last Refreshed:")
    return main_embed


async def cwl_ranking_create(bot: CustomClient, clan: coc.Clan):
    try:
        group = await bot.coc_client.get_league_group(clan.tag)
        state = group.state
        if str(state) == "preparation" and len(group.rounds) == 1:
            return {clan.tag: None}
        if str(group.season) != bot.gen_season_date():
            return {clan.tag: None}
    except:
        return {clan.tag: None}

    star_dict = defaultdict(int)
    dest_dict = defaultdict(int)
    tag_to_name = defaultdict(str)

    rounds = group.rounds
    for round in rounds:
        for war_tag in round:
            war = await bot.coc_client.get_league_war(war_tag)
            if str(war.status) == "won":
                star_dict[war.clan.tag] += 10
            elif str(war.status) == "lost":
                star_dict[war.opponent.tag] += 10
            tag_to_name[war.clan.tag] = war.clan.name
            tag_to_name[war.opponent.tag] = war.opponent.name
            for player in war.members:
                attacks = player.attacks
                for attack in attacks:
                    star_dict[player.clan.tag] += attack.stars
                    dest_dict[player.clan.tag] += attack.destruction

    star_list = []
    for tag, stars in star_dict.items():
        destruction = dest_dict[tag]
        name = tag_to_name[tag]
        star_list.append([tag, stars, destruction])

    sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
    place= 1
    for item in sorted_list:
        promo = [x["promo"] for x in war_leagues["items"] if x["name"] == clan.war_league.name][0]
        demo = [x["demote"] for x in war_leagues["items"] if x["name"] == clan.war_league.name][0]
        if place <= promo:
            emoji = "<:warwon:932212939899949176>"
        elif place >= demo:
            emoji = "<:warlost:932212154164183081>"
        else:
            emoji = "<:dash:933150462818021437>"
        tag = item[0]
        stars = str(item[1])
        dest = str(item[2])
        if place == 1:
            rank = f"{place}st"
        elif place == 2:
            rank = f"{place}nd"
        elif place == 3:
            rank = f"{place}rd"
        else:
            rank = f"{place}th"
        if tag == clan.tag:
            tier = str(clan.war_league.name).count("I")
            return {clan.tag : f"{emoji}`{rank}` {cwl_league_emojis(clan.war_league.name)}{SUPER_SCRIPTS[tier]}"}
        place += 1
