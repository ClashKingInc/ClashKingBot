import disnake
import coc

from datetime import datetime
from CustomClasses.CustomBot import CustomClient
from pytz import utc
from collections import defaultdict
from utils.general import create_superscript
from utils.clash import cwl_league_emojis, leagueAndTrophies
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.Misc import WarPlan

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
    embed.add_field(name=f"**War Against**", value=f"[**{war.opponent.name}**]({war.opponent.share_link})\n­\n",inline=False)


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


async def calculate_potential_stars(bot: CustomClient, num_ones, num_twos, num_threes, done_amount, total_left):
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
