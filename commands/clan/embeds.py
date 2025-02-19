from collections import defaultdict

import coc
import disnake
import pendulum as pend
from disnake import Embed
from classes.bot import CustomClient

from utility.discord.commands import register_button


from classes.cocpy.clan import BaseClan
from .utils import townhall_composition, super_troop_composition


@register_button('clancompo', parser='_:clan:type')
async def clan_composition(
        bot: CustomClient,
        clan: BaseClan,
        type: str,
        embed_color: disnake.Color,
        locale: disnake.Locale = disnake.Locale.en_US,
):
    _, locale = bot.get_localizator(locale=locale)

    bucket = defaultdict(int)

    tag_to_location = None
    country_to_code = {}
    if type == 'Location':
        tag_to_location = await bot.ck_client.get_player_locations(player_tags=clan.member_tags)
        country_to_code = {p.country.name: p.country.code.lower() for p in tag_to_location}

    for member in clan.members:
        if type == 'Townhall':
            if member.town_hall == 0:
                continue
            bucket[member.town_hall] += 1
        elif type == 'Trophies':
            if member.trophies >= 1000:
                bucket[str((member.trophies // 1000) * 1000)] += 1
            else:
                bucket['100'] += 1
        elif type == 'Location':
            if member.tag in tag_to_location:
                location = tag_to_location[member.tag]
                bucket[location.country.name] += 1
        elif type == 'Role':
            bucket[member.role.in_game_name] += 1
        elif type == 'League':
            bucket[member.league.name] += 1

    if not bucket:
        return disnake.Embed(description=_("no-data-found-clan"), color=disnake.Color.red())

    text = ''
    total = 0
    field_to_sort = 1 if type != "Townhall" else 0
    for key, value in sorted(bucket.items(), key=lambda x: x[field_to_sort], reverse=True):
        icon = ''
        if type == 'Townhall':
            icon = bot.fetch_emoji(int(key))
            total += int(key) * value
        elif type == 'Location':
            icon = f':flag_{country_to_code.get(key)}:'
        elif type == 'League':
            icon = bot.fetch_emoji(name=key)

        formats = {
            'Townhall': '`{value:2}` {icon}`TH{key} `\n',
            'Trophies': '`{value:2}` {icon}`{key}+ Trophies`\n',
            'Location': '`{value:2}` {icon}`{key}`\n',
            'Role': '`{value:2}` {icon}`{key}`\n',
            'League': '`{value:2}` {icon}`{key}`\n',
        }
        text += f'{formats.get(type).format(key=key,value=_(value), icon=icon)}'

    footer_text = _("num-accounts", values={"num" : clan.member_count})
    if type == 'Townhall':
        footer_text += f' | {_("average-townhall")}: {round((total / clan.member_count), 2)}'

    embed = disnake.Embed(
        title=_(
            'clan-compo-title',
            values={
                "clan_name": clan.name,
                "type": _(type)
            }
        ),
        description=text,
        color=embed_color
    )
    embed.set_thumbnail(url=clan.badge.large)
    embed.set_footer(text=footer_text)
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


@register_button('clandetailed', parser='_:clan')
async def detailed_clan_board(
        bot: CustomClient,
        clan: BaseClan,
        server: disnake.Guild,
        embed_color: disnake.Color,
        locale: disnake.Locale = disnake.Locale.en_US,
):
    _, locale = bot.get_localizator(locale=locale)


    db_clan = await bot.ck_client.get_server_clan_settings(server_id=server and server.id, clan_tag=clan.tag, silent=True)

    clan_ranking = await bot.ck_client.get_clan_ranking(clan_tag=clan.tag)


    clan_leader = coc.utils.get(clan.members, role=coc.Role.leader)


    war_loss = max(clan.war_losses, 0) if clan.public_war_log else _("hidden-log")
    win_rate = round((clan.war_wins / max(war_loss, 1)), 2) if clan.public_war_log else _("hidden-log")

    if str(clan.location) == 'International':
        flag = bot.emoji.earth
    elif clan.location:
        flag = f':flag_{clan.location.country_code.lower()}:'
    else:
        flag = '🏳️'

    rank_text = f'{_("rankings")}: {bot.emoji.earth} {clan_ranking.global_rank} | {flag} {clan_ranking.local_ranking}\n'
    if not clan_ranking.local_rank and not clan_ranking.global_rank:
        rank_text = f''

    hall_level = coc.utils.get(clan.capital_districts, id=70000000).hall_level
    clan_capital_text = (
        f'{_("capital-league")}: {bot.fetch_emoji(clan.capital_league)}{clan.capital_league}\n'
        f'{_("capital-points")}: {bot.emoji.capital_trophy}{clan.capital_points}\n'
        f"{_("capital-hall")}: {bot.fetch_emoji(f'Capital_Hall{hall_level}')} {_("level")} {hall_level}\n"
    )

    clan_type_converter = {
        'open': _("anyone-can-join"),
        'inviteOnly': _("invite-only"),
        'closed': _("closed"),
    }
    embed = Embed(
        title=f'**{clan.name}**',
        description=(
            f'{_("tag")}: [{clan.tag}]({clan.share_link})\n'
            f'{_("trophies")}: {bot.emoji.trophy} {clan.points} | {bot.emoji.versus_trophy} {clan.builder_base_points}\n'
            f'{_("requirements")}: {bot.emoji.trophy}{clan.required_trophies} | '
            f'{bot.fetch_emoji(clan.required_townhall)}{clan.required_townhall}\n'
            f'{_("type")}: {clan_type_converter[clan.type]}\n'
            f'{_("clan-location")}: {flag} {clan.location.name if clan.location else _("not-set")}\n'
            f'{rank_text}'
            f'{_("leader")}: {clan_leader.name}\n'
            f'{_("level")}: {clan.level} \n'
            f'{_("members")}: {bot.emoji.people}{clan.member_count}/50\n\n'
            f'{_("cwl")}: {bot.fetch_emoji(f"CWL_{clan.war_league}")}{clan.war_league}\n'
            f'{_("wars-won")}: {bot.emoji.up_green_arrow}{clan.war_wins}\n'
            f'{_("wars-lost")}: {bot.emoji.down_red_arrow}{war_loss}\n'
            f'{_("win-streak")}: {bot.emoji.double_up_arrow}{clan.war_win_streak}\n'
            f'{_("win-ratio")}: {bot.emoji.ratio}{win_rate}\n\n'
            f'{clan_capital_text}\n'
            f'{_("clan-description")}: {clan.description}'
        ),
        color=embed_color,
    )

    clan_totals = await bot.ck_client.get_clan_totals(clan_tag="#VY2J0LL", player_tags=clan.member_tags)
    formatted_stats = (
        f"Clan Games: {clan_totals.clan_games_points:,} Points\n"
        f"Capital Gold: {clan_totals.clan_capital_donated:,} Donated\n"
        f"Donos: {bot.emoji.up_green_arrow}{clan_totals.troops_donated:,}, "
        f"{bot.emoji.down_red_arrow}{clan_totals.troops_received:,}\n"
        f"Active Daily: {clan_totals.activity_per_day} players/avg\n"
        f"Activity Score: {clan_totals.activity_score}\n"
        f"Active Last 48h: {clan_totals.activity_last_48h} players"
    )
    embed.add_field(name="Season Stats", value=formatted_stats)

    th_comp = townhall_composition(bot=bot, players=clan.members)
    super_troop_comp = super_troop_composition(bot=bot, players=clan.members)

    embed.add_field(name='**Townhall Composition:**', value=th_comp, inline=False)
    embed.add_field(name='**Boosted Super Troops:**', value=super_troop_comp, inline=False)

    embed.set_thumbnail(url=clan.badge.large)
    if db_clan and db_clan.category:
        embed.set_footer(text=f'Category: {db_clan.category}')
    embed.timestamp = pend.now(tz=pend.UTC)

    return embed


@register_button('clanbasic', parser='_:clan')
async def basic_clan_board(
    bot: CustomClient,
    clan: coc.Clan,
    embed_color: disnake.Color = disnake.Color.green(),
):
    leader = coc.utils.get(clan.members, role=coc.Role.leader)

    warwin = clan.war_wins
    warloss = clan.war_losses or 'Hidden Log'
    winstreak = clan.war_win_streak
    if clan.public_war_log:
        winrate = round((warwin / (warloss if clan.war_losses != 0 else 1)), 2)
    else:
        winrate = 'Hidden Log'

    if str(clan.location) == 'International' or clan.location is None:
        flag = bot.emoji.earth.emoji_string
    else:
        flag = f':flag_{clan.location.country_code.lower()}:'

    embed = disnake.Embed(
        title=f'**{clan.name}**',
        description=f'Tag: [{clan.tag}]({clan.share_link})\n'
        f'Trophies: {bot.emoji.trophy} {clan.points} | {bot.emoji.versus_trophy} {clan.builder_base_points}\n'
        f'Required Trophies: {bot.emoji.trophy} {clan.required_trophies}\n'
        f'Location: {flag} {clan.location}\n\n'
        f'Leader: {leader.name}\n'
        f'Level: {clan.level} \n'
        f'Members: {bot.emoji.people}{clan.member_count}/50\n\n'
        f'CWL: {bot.fetch_emoji(f"CWL_{clan.war_league}")}{str(clan.war_league)}\n'
        f'Wars Won: {bot.emoji.up_green_arrow}{warwin}\nWars Lost: {bot.emoji.down_red_arrow}{warloss}\n'
        f'War Streak: {bot.emoji.ratio}{winstreak}\nWin Ratio: {bot.emoji.ratio}{winrate}\n\n'
        f'Description: {clan.description}',
        color=embed_color,
    )

    embed.set_thumbnail(url=clan.badge.large)
    return embed


@register_button('clanmini', parser='_:clan')
async def minimalistic_clan_board(
    bot: CustomClient,
    server: disnake.Guild,
    clan: coc.Clan,
    embed_color: disnake.Color = disnake.Color.green(),
):
    db_clan = await bot.clan_db.find_one({'$and': [{'tag': clan.tag}, {'server': server.id}]})
    db_clan = db_clan or {}
    ctg = db_clan.get('category', 'General')
    category = f'{ctg} Clan'

    embed = disnake.Embed(
        description=f'**[{clan.name}]({clan.share_link})**\n{category} ({clan.member_count}/50)\n{clan.war_league.name}',
        color=embed_color,
    )
    embed.set_thumbnail(url=clan.badge.large)
    return embed





