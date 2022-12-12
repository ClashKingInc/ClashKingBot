import coc
from CustomClasses.CustomPlayer import LegendRanking
from disnake import Embed, Color
from disnake.utils import get
from utils.discord_utils import fetch_emoji
from collections import defaultdict
from Clan.ClanUtils import (
    clan_th_comp,
    clan_super_troop_comp,
    league_and_trophies_emoji)
import emoji


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
