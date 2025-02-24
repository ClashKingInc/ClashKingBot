from collections import defaultdict

import coc
import disnake
import pendulum as pend
from chat_exporter.ext.html_generator import embed_description
from disnake import Embed
from classes.bot import CustomClient
from utility.clash.other import league_emoji
from num2words import num2words

from utility.discord.commands import register_button
from utility.general import create_superscript
from utility.constants import SHORT_CLAN_LINK
from utility.time import gen_season_date
from itertools import groupby

from classes.cocpy.clan import CustomClan, CustomClanMember
from .utils import townhall_composition


@register_button('clancompo', parser='_:clan:type')
async def clan_composition(
        bot: CustomClient,
        clan: CustomClan,
        type: str,
        embed_color: disnake.Color,
        locale: disnake.Locale,
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
        text += f'{formats.get(type).format(key=key, value=value, icon=icon)}'

    footer_text = _("num-accounts", num=clan.member_count)
    if type == 'Townhall':
        footer_text += f' | {_("average-townhall")}: {round((total / clan.member_count), 2)}'

    embed = disnake.Embed(
        title=_(
            'clan-compo-title',
            clan_name=clan.name,
            type=_(type.lower()),
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
        clan: CustomClan,
        server: disnake.Guild,
        embed_color: disnake.Color,
        locale: disnake.Locale,
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

    rank_text = f'{_("rankings")}: {bot.emoji.earth} {clan_ranking.global_rank} | {flag} {clan_ranking.local_rank}\n'

    if not clan_ranking.local_rank and not clan_ranking.global_rank:
        rank_text = f''

    hall_level = coc.utils.get(clan.capital_districts, id=70000000).hall_level
    clan_capital_text = (
        f'{_("capital-league")}: {bot.fetch_emoji(clan.capital_league.name)}{clan.capital_league}\n'
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
            f'{_("clan-tag")}: [{clan.tag}]({clan.share_link})\n'
            f'{_("trophies")}: {bot.emoji.trophy} {clan.points} | {bot.emoji.versus_trophy} {clan.builder_base_points}\n'
            f'{_("requirements")}: {bot.emoji.trophy}{clan.required_trophies} | '
            f'{bot.fetch_emoji(clan.required_townhall)}{clan.required_townhall}\n'
            f'{_("type")}: {clan_type_converter[clan.type]}\n'
            f'{_("clan-location")}: {flag} {clan.location.name if clan.location else _("not-set")}\n'
            f'{rank_text}'
            f'{_("leader")}: {clan_leader.name}\n'
            f'{_("level")}: {clan.level} \n'
            f'{_("members")}: {bot.emoji.people}{clan.member_count}/50\n\n'
            f'{_("cwl")}: {bot.fetch_emoji(f"CWL {clan.war_league}")}{clan.war_league}\n'
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
        f"{_("clan-games-points", points=clan_totals.clan_games_points)}\n"
        f"{_("capital-gold-donated", donated=clan_totals.clan_capital_donated)}\n"
        f"{_("total-clan-donations", 
             donated_emoji=bot.emoji.up_green_arrow.emoji_string,
             donated=clan_totals.troops_donated,
             received_emoji=bot.emoji.down_red_arrow.emoji_string,
             received=clan_totals.troops_received,
             )}\n"
        f"{_("active-daily", num=clan_totals.activity_per_day)}\n"
        f"{_("active-last-48", num=clan_totals.activity_last_48h)}\n"
    )
    embed.add_field(name=_("season-stats"), value=formatted_stats)

    th_comp = townhall_composition(bot=bot, players=clan.members)
    embed.add_field(name=_("townhall-composition"), value=th_comp, inline=False)

    embed.set_thumbnail(url=clan.badge.large)
    if db_clan and db_clan.category:
        embed.set_footer(text=_("clan-category", category=db_clan.category))
    embed.timestamp = pend.now(tz=pend.UTC)

    return embed


@register_button('clanbasic', parser='_:clan')
async def basic_clan_board(
    bot: CustomClient,
    clan: CustomClan,
    embed_color: disnake.Color,
    locale: disnake.Locale,
):
    _, locale = bot.get_localizator(locale=locale)

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

    rank_text = f'{_("rankings")}: {bot.emoji.earth} {clan_ranking.global_rank} | {flag} {clan_ranking.local_rank}\n'

    if not clan_ranking.local_rank and not clan_ranking.global_rank:
        rank_text = f''

    hall_level = coc.utils.get(clan.capital_districts, id=70000000).hall_level
    clan_capital_text = (
        f'{_("capital-league")}: {bot.fetch_emoji(clan.capital_league.name)}{clan.capital_league}\n'
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
            f'{_("clan-tag")}: [{clan.tag}]({clan.share_link})\n'
            f'{_("trophies")}: {bot.emoji.trophy} {clan.points} | {bot.emoji.versus_trophy} {clan.builder_base_points}\n'
            f'{_("requirements")}: {bot.emoji.trophy}{clan.required_trophies} | '
            f'{bot.fetch_emoji(clan.required_townhall)}{clan.required_townhall}\n'
            f'{_("type")}: {clan_type_converter[clan.type]}\n'
            f'{_("clan-location")}: {flag} {clan.location.name if clan.location else _("not-set")}\n'
            f'{rank_text}'
            f'{_("leader")}: {clan_leader.name}\n'
            f'{_("level")}: {clan.level} \n'
            f'{_("members")}: {bot.emoji.people}{clan.member_count}/50\n\n'
            f'{_("cwl")}: {bot.fetch_emoji(f"CWL {clan.war_league}")}{clan.war_league}\n'
            f'{_("wars-won")}: {bot.emoji.up_green_arrow}{clan.war_wins}\n'
            f'{_("wars-lost")}: {bot.emoji.down_red_arrow}{war_loss}\n'
            f'{_("win-streak")}: {bot.emoji.double_up_arrow}{clan.war_win_streak}\n'
            f'{_("win-ratio")}: {bot.emoji.ratio}{win_rate}\n\n'
            f'{clan_capital_text}\n'
            f'{_("clan-description")}: {clan.description}'
        ),
        color=embed_color,
    )
    embed.set_thumbnail(url=clan.badge.large)
    return embed


@register_button('clanmini', parser='_:clan')
async def minimalistic_clan_board(
    bot: CustomClient,
    clan: coc.Clan,
    embed_color: disnake.Color,
    locale: disnake.Locale,
):
    _, locale = bot.get_localizator(locale=locale)

    if str(clan.location) == 'International':
        flag = bot.emoji.earth
    elif clan.location:
        flag = f':flag_{clan.location.country_code.lower()}:'
    else:
        flag = '🏳️'

    clan_ranking = await bot.ck_client.get_clan_ranking(clan_tag=clan.tag)
    rank_text = f'{_("rankings")}: {bot.emoji.earth} {clan_ranking.global_rank} | {flag} {clan_ranking.local_rank}\n'
    if not clan_ranking.local_rank and not clan_ranking.global_rank:
        rank_text = f''

    embed = disnake.Embed(
        description=f'**[{clan.name}]({clan.share_link})**\n'
                    f'{bot.emoji.trophy}{clan.points} ({clan.member_count}/50)\n'
                    f'{rank_text}'
                    f'{clan.war_league.name}',
        color=embed_color,
    )
    embed.set_thumbnail(url=clan.badge.large)
    return embed


@register_button('clandonos', parser='_:clan:season:townhall:limit:sort_by:sort_order')
async def clan_donations(
    bot: CustomClient,
    clan: CustomClan,
    season: str,
    sort_by: str,
    sort_order: str,
    townhall: int,
    limit: int,
    embed_color: disnake.Color,
    locale: disnake.Locale
):
    _, locale = bot.get_localizator(locale=locale)

    season = season or gen_season_date()

    donation_data = await bot.ck_client.get_clan_donations(clan_tag=clan.tag, season=season)

    for member in clan.members:
        if member.tag in donation_data:
            member.donations = max(member.donations, donation_data[member.tag].donated)
            member.received = max(member.received, donation_data[member.tag].received)

    #only get matching townhall members, according to filter
    members: list[CustomClanMember] = [member for member in clan.members if townhall is None or member.town_hall == townhall]

    sort_map = {
        "Name" : "name",
        "Townhall" : "town_hall",
        "Donations" : "donations",
        "Received" : "received",
        "Ratio" : "donation_ratio"
    }

    members.sort(
        key=lambda x: x.__getattribute__(sort_map.get(sort_by)),
        reverse=(sort_order.lower() == 'descending'),
    )

    text = '` #  DON   REC  NAME        `\n'
    total_donated = 0
    total_received = 0
    for count, member in enumerate(members[:limit], 1):
        text += f'`{count:2} {member.donations:5} {member.received:5} ' \
                f'{disnake.utils.escape_markdown(member.name)[:13]:13}`' \
                f'[{create_superscript(member.town_hall)}]({member.share_link})\n'
        total_donated += member.donations
        total_received += member.received

    embed = disnake.Embed(description=f'{text}', color=embed_color)
    embed.set_author(
        name=_("clan-donations-title", clan_name=clan.name, num=min(limit, len(members))),
        icon_url=clan.badge.url,
    )
    embed.set_footer(
        icon_url=bot.emoji.clan_castle.partial_emoji.url,
        text=_("clan-donations-footer",
               type=sort_by,
               total_donated=total_donated,
               total_received=total_received,
               season=season),
    )

    embed.timestamp = pend.now(tz=pend.UTC)
    return embed



@register_button('clanwarlog', parser='_:clan:limit')
async def war_log(
    bot: CustomClient,
    clan: CustomClan,
    limit: int,
    embed_color: disnake.Color,
    locale: disnake.Locale
):
    _, locale = bot.get_localizator(locale=locale)

    embed_description = ''

    if clan.public_war_log:
        war_log = await bot.coc_client.get_war_log(clan.tag, limit=limit)
    else:
        war_log = await bot.ck_client.get_previous_clan_wars(clan_tag=clan.tag, limit=limit)

    for war in war_log: #type: coc.ClanWarLogEntry | coc.ClanWar
        if isinstance(war, coc.ClanWarLogEntry) and war.is_league_entry:
            continue

        clan_attack_count = war.clan.attacks_used

        opponent_name = f'[\u200e{war.opponent.name}]({SHORT_CLAN_LINK + war.opponent.tag.replace("#", "")})'
        if (war.clan.stars > war.opponent.stars or
                (war.clan.stars == war.opponent.stars and war.clan.destruction > war.opponent.destruction)):
            status = bot.emoji.up_green_arrow
            op_status = _("win-vs", clan_name=opponent_name)

        elif (war.opponent.stars == war.clan.stars) and (war.clan.destruction == war.opponent.destruction):
            status = bot.emoji.grey_dash
            op_status = _("draw-vs", clan_name=opponent_name)

        else:
            status = bot.emoji.down_red_arrow
            op_status = _("loss-vs", clan_name=opponent_name)

        time = f'<t:{int(war.end_time.time.replace(tzinfo=pend.UTC).timestamp())}:R>'
        embed_description += (
            f'{status}**{op_status}**\n'
            f'({war.team_size} vs {war.team_size}){create_superscript(war.attacks_per_member)} | {time}\n'
            f'{war.clan.stars} ★ {war.opponent.stars} | '
            f'{clan_attack_count}/{war.team_size * war.attacks_per_member} | {round(war.clan.destruction, 1)}%\n'
        )

    embed_description = embed_description or _("empty-warlog")

    embed = Embed(description=embed_description, color=embed_color)
    embed.set_author(
        icon_url=clan.badge.large,
        name=_(f'clan-warlog-title', clan_name=clan.name, num=min(limit, len(war_log))),
    )
    embed.timestamp = pend.now(tz=pend.UTC)
    if not clan.public_war_log:
        embed.set_footer(text=_("clan-warlog-hidden-info"))
    return embed


@register_button('clancwlperf', parser='_:clan')
async def cwl_performance(
        bot: CustomClient,
        clan: CustomClan,
        embed_color: disnake.Color,
        limit: int,
        locale: disnake.Locale
):
    _, locale = bot.get_localizator(locale=locale)
    limit = min(limit, 20)

    cwl_ranking_history = await bot.ck_client.get_cwl_ranking_history(clan_tag=clan.tag)
    thresholds = await bot.ck_client.get_cwl_league_thresholds()

    description = ""
    for year, items in groupby(cwl_ranking_history[:limit], key=lambda c: c.season[:4]):
        year_text = ""
        for cwl in items:
            # Find thresholds for the current league
            promo, demo = next(((t.promo, t.demote) for t in thresholds if t.name == cwl.league), (0, 0))

            # Determine the appropriate emoji
            place_emoji = (
                bot.emoji.up_green_arrow.str if cwl.rank <= promo else
                bot.emoji.down_red_arrow.str if cwl.rank >= demo else
                "▫️"
            )

            date = pend.from_format(cwl.season, "YYYY-MM")
            text = _("cwl-ranking-line",
                     place_emoji=place_emoji,
                     league_emoji=bot.fetch_emoji(f"CWL {cwl.league}").str,
                     superscript=create_superscript(len(cwl.league.split(" ")[-1])),
                     place=num2words(cwl.rank, to='ordinal_num', lang=locale.value.replace("-", "_")),
                     month=date.format("MMMM", locale=locale.value.replace("-", "_")).capitalize(),
                    )
            text += f"\n-# ★{cwl.stars} | {cwl.destruction:.2f}% | ▲{cwl.rounds_won} | ▼{cwl.rounds_lost}"

            year_text += f"{text}\n"

        # Add the field for the year if there is any text
        if year_text:
            description += f'**{year}**\n{year_text}\n'

    if not description:
        description = 'No prior cwl data'

    embed = Embed(title=f'**{clan.name} CWL History**', description=description, color=embed_color)

    embed.set_thumbnail(url=clan.badge.large)

    embed.timestamp = pend.now(tz=pend.UTC)
    return embed





