import asyncio
import calendar
import io
import random

import aiohttp
import coc
import disnake
import emoji
import matplotlib
import concurrent.futures

matplotlib.use('Agg')
from datetime import datetime
from typing import List

import matplotlib.pyplot as plt
import pendulum as pend
from babel import Locale
from babel.dates import get_month_names
from coc import Clan, enums, utils
from PIL import Image, ImageDraw, ImageFont
from pytz import utc

from classes.bot import CustomClient
from classes.DatabaseClient.Classes.player import LegendDay, LegendPlayer
from utility.cdn import general_upload_to_cdn
from utility.clash.other import gen_legend_date, gen_season_date
from utility.constants import HERO_EQUIPMENT, POSTER_LIST
from utility.discord_utils import register_button
from utility.general import create_superscript


@register_button('legendday', parser='_:player')
async def legend_day_overview(
    bot: CustomClient,
    player: coc.Player,
    embed_color: disnake.Color,
    locale: disnake.Locale,
):
    player = await bot.ck_client.get_legend_player(player=player)
    legend_day = player.get_legend_day()

    _, locale = bot.get_localizator(locale=locale)
    embed = disnake.Embed(
        description=f"**{_('legend-overview')}** | [{_('profile')}]({player.share_link})\n"
        + f"{_('start')} {bot.fetch_emoji('Legend League')} {player.trophy_start} | {_('now')}  {bot.fetch_emoji('Legend League')} {player._.trophies}\n"
        + f"- {_('attacks-for-trophies', values={'num_attacks' : int(legend_day.num_attacks), 'attack_sum' : legend_day.attack_sum})}\n"
        + f"- {_('defenses-for-trophies', values={'num_defenses' : int(legend_day.num_defenses), 'defense_sum' : legend_day.defense_sum})}\n"
        + f"- {_('net-trophies', values={'net_gain' : legend_day.net_gain})}\n"
        + f"- {_('streak', values={'triple_streak' : player.streak})}",
        color=embed_color,
    )

    global_ranking_text = player.ranking.global_ranking
    if isinstance(global_ranking_text, int):
        lowest_rank = await bot.legend_rankings.find({}).sort([('rank', -1)]).limit(1).to_list(length=1)
        lowest_rank = lowest_rank[0].get('rank')
        curr_rank = player.ranking.global_ranking
        if player.ranking.global_ranking < 100:
            curr_rank = 100
        mid_calc = (curr_rank / lowest_rank) * 100
        perc_of_total = round(mid_calc, 2 if mid_calc < 1 else None)
        global_ranking_text = f"{player.ranking.global_ranking} {_('top-ranking', values={'perc_of_total' : perc_of_total})}"

    embed.add_field(
        name=f"**{_('rankings')}**",
        value=f"- {bot.emoji.earth} {global_ranking_text}\n"
              f"- {player.ranking.flag} {player.ranking.local_ranking}\n"
              f"- {_('country')}: {player.ranking.country}\n"
              f"[*Stats seem wrong? FAQ*](https://docs.clashking.xyz/faq#the-legend-stats-are-wrong)",
        inline=False,
    )

    embed.set_author(name=f'{player._.name} | {player.clan_name}', icon_url=player.clan_badge)
    embed.set_thumbnail(url=player.townhall.image_url)

    off = ''
    gears_used = set()
    for hit in legend_day.attacks:
        if hit.timestamp is None:
            off += f'{bot.emoji.clash_sword} +{hit.change}\n'
        else:
            for gear in hit.hero_gear:
                gears_used.add(gear)
            off += f'{bot.emoji.clash_sword} +{hit.change} {bot.timestamper(hit.timestamp).relative}\n'

    gear_text = ''

    for hero in enums.HOME_BASE_HERO_ORDER:
        emoji_text = ''
        for gear in gears_used:
            gear_hero = HERO_EQUIPMENT.get(gear.name)
            if gear_hero == hero:
                emoji_text += f'{bot.fetch_emoji(gear.name)}{create_superscript(gear.level)}'
        if emoji_text != '':
            gear_text += f'{bot.fetch_emoji(name=hero)} | {emoji_text}\n'

    defi = ''
    for d in legend_day.defenses:
        defi += f'{bot.emoji.shield.emoji_string} -{d.change} {bot.timestamper(d.timestamp).relative}\n'

    if off == '':
        off = _('no-attacks')
    if defi == '':
        defi = _('no-defenses')
    if not gear_text:
        gear_text = _('no-equipment')

    embed.add_field(name=f"**{_('offense')}**", value=off, inline=True)
    embed.add_field(name=f"**{_('defense')}**", value=defi, inline=True)
    embed.add_field(name=f"**{_('equipment-used')}**", value=gear_text, inline=False)
    embed.set_footer(text=player.tag)

    poster = await legend_poster(bot=bot, player=player)
    embed.set_image(file=poster)

    return embed


@register_button('legendseason', parser='_:player')
async def legend_season_overview(
    bot: CustomClient,
    player: coc.Player,
    embed_color: disnake.Color,
    locale: disnake.Locale,
):
    _, locale = bot.get_localizator(locale=locale)

    player = await bot.ck_client.get_legend_player(player=player)
    season_stats = player.get_legend_season()
    text = f"**{_('attacks-won')}:** {player._.attack_wins} | **{_('defenses-won')}:** {player._.defense_wins}\n"

    start = utils.get_season_start().replace(tzinfo=utc).date()
    now = datetime.now(tz=utc).date()
    now_ = datetime.now(tz=utc)
    current_season_progress = now - start
    current_season_progress = current_season_progress.days
    if now_.hour < 5:
        current_season_progress -= 1

    day = 0
    text += f"```{_('legend-day-headings')}\n"
    for legend_day in season_stats.values():  # type: LegendDay
        day += 1
        day_text = f'{day:<2}'
        trophy_finish = ''
        if legend_day.finished_trophies is not None:
            trophy_finish = f' {legend_day.finished_trophies:<4}'
        attack_text = f'{legend_day.attack_sum}{legend_day.num_attacks.superscript}'
        defense_text = f'{legend_day.defense_sum}{legend_day.num_defenses.superscript}'
        text += f'{day_text}  {attack_text:<4} {defense_text:<4}{trophy_finish}\n'
        if day == current_season_progress:
            break

    if day == 0:
        text += f"\n**{_('no-previous-days')}**"
    text += '```'

    embed = disnake.Embed(title=f"{_('season-legends-overview')}", description=text, color=embed_color)

    embed.set_author(
        name=f'{player._.name} | {player.clan_name}',
        icon_url=player.clan_badge,
        url=player.share_link,
    )
    embed.set_thumbnail(url=player.townhall.image_url)

    month = start.month
    month = month if month != 12 else 0
    month_names = get_month_names('wide', locale=Locale.parse(locale.value.replace('-', '_')))
    month = month_names[month + 1]

    embed.set_footer(text=f"{_('legend-season', values={'month' : month, 'year' : start.year})}")

    return embed


async def legend_poster(bot: CustomClient, player: coc.Player | LegendPlayer, background: str = None) -> disnake.File:
    if isinstance(player, coc.Player):
        player = await bot.ck_client.get_legend_player(player=player)
    start = utils.get_season_start().replace(tzinfo=utc).date()
    today = datetime.now(tz=utc).date()
    length = today - start
    month = start.month
    if month == 12:
        month = 0
    month = calendar.month_name[month + 1]
    trophies = player._.trophies
    season = gen_season_date()

    season_stats = player.get_legend_season(season=season)
    season_stats = list(season_stats.values())
    season_stats = season_stats[0 : length.days + 1]

    y = [5000] + [legend_day.finished_trophies for legend_day in season_stats if legend_day.finished_trophies is not None]
    x = [spot for spot in range(0, len(y))]

    fig = plt.figure(dpi=100)
    ax = plt.subplot()
    ax.plot(
        x,
        y,
        color='white',
        linestyle='dashed',
        linewidth=3,
        marker='*',
        markerfacecolor='white',
        markeredgecolor='yellow',
        markersize=20,
    )
    plt.ylim(min(y) - 25, max(y) + 100)

    plt.xlim(left=0, right=len(season_stats))
    plt.xlabel('Day', color='yellow', fontsize=14)

    plt.locator_params(axis='both', integer=True, tight=True)
    plt.gca().spines['top'].set_color('yellow')
    plt.gca().spines['bottom'].set_color('yellow')
    plt.gca().spines['left'].set_color('yellow')
    plt.gca().spines['right'].set_color('yellow')
    plt.gca().tick_params(axis='x', colors='yellow')
    plt.gca().tick_params(axis='y', colors='yellow')

    plt.ylabel('Trophies', color='yellow', fontsize=14)
    fig.savefig('assets/poster_graph.png', transparent=True)
    plt.close(fig)

    graph = Image.open('assets/poster_graph.png')
    if background is None:
        poster = Image.open(f'assets/backgrounds/{random.choice(list(POSTER_LIST.values()))}.png')
    else:
        poster = Image.open(f'assets/backgrounds/{POSTER_LIST.get(background)}.png')

    poster.paste(graph, (1175, 475), graph.convert('RGBA'))

    font = ImageFont.truetype('assets/fonts/code.ttf', 80)
    font2 = ImageFont.truetype('assets/fonts/blogger.ttf', 35)
    font3 = ImageFont.truetype('assets/fonts/blogger.ttf', 60)
    font4 = ImageFont.truetype('assets/fonts/blogger.ttf', 37)
    font5 = ImageFont.truetype('assets/fonts/blogger.ttf', 20)
    font6 = ImageFont.truetype('assets/fonts/blogger.ttf', 40)

    # add clan badge & text
    if player._.clan is not None:
        # clan = await player.get_detailed_clan()
        async def fetch(url, session):
            async with session.get(url) as response:
                image_data = io.BytesIO(await response.read())
                return image_data

        tasks = []
        async with aiohttp.ClientSession() as session:
            tasks.append(fetch(player._.clan.badge.large, session))
            responses = await asyncio.gather(*tasks)
            await session.close()
        badge = Image.open(responses[0])
        size = 275, 275
        badge.thumbnail(size, Image.LANCZOS)
        A = badge.getchannel('A')
        newA = A.point(lambda i: 128 if i > 0 else 0)
        badge.putalpha(newA)
        poster.paste(badge, (1350, 110), badge.convert('RGBA'))

        watermark = Image.new('RGBA', poster.size)
        waterdraw = ImageDraw.ImageDraw(watermark, 'RGBA')
        waterdraw.text((1488, 70), player._.clan.name, anchor='mm', font=font)
        watermask = watermark.convert('L').point(lambda x: min(x, 100))
        watermark.putalpha(watermask)
        poster.paste(watermark, None, watermark)

    stats = player.get_legend_season_stats()

    draw = ImageDraw.Draw(poster)
    draw.text(
        (585, 95),
        emoji.replace_emoji(player._.name, ' '),
        anchor='mm',
        fill=(255, 255, 255),
        font=font,
    )
    draw.text(
        (570, 175),
        f'Stats collected from {len(y)} days of data',
        anchor='mm',
        fill=(255, 255, 255),
        font=font5,
    )
    draw.text(
        (360, 275),
        f'+{stats.average_offense} CUPS A DAY',
        anchor='mm',
        fill=(255, 255, 255),
        font=font2,
    )
    draw.text(
        (800, 275),
        f'-{stats.average_defense} CUPS A DAY',
        anchor='mm',
        fill=(255, 255, 255),
        font=font2,
    )
    draw.text(
        (570, 400),
        f'{stats.net} CUPS A DAY',
        anchor='mm',
        fill=(255, 255, 255),
        font=font2,
    )
    draw.text(
        (1240, 400),
        f'{trophies} | {month} {start.year}',
        fill=(255, 255, 255),
        font=font3,
    )
    draw.text(
        (295, 670),
        f'{stats.offensive_one_star}%',
        anchor='mm',
        fill=(255, 255, 255),
        font=font4,
    )
    draw.text(
        (295, 790),
        f'{stats.offensive_two_star}%',
        anchor='mm',
        fill=(255, 255, 255),
        font=font4,
    )
    draw.text(
        (295, 910),
        f'{stats.offensive_three_star}%',
        anchor='mm',
        fill=(255, 255, 255),
        font=font4,
    )

    draw.text(
        (840, 670),
        f'{stats.defensive_one_star}%',
        anchor='mm',
        fill=(255, 255, 255),
        font=font4,
    )
    draw.text(
        (840, 790),
        f'{stats.defensive_two_star}%',
        anchor='mm',
        fill=(255, 255, 255),
        font=font4,
    )
    draw.text(
        (840, 910),
        f'{stats.defensive_three_star}%',
        anchor='mm',
        fill=(255, 255, 255),
        font=font4,
    )
    # draw.text((75, 1020), f"{month} {start.year} Season", fill=(255, 255, 255), font=font4)

    if isinstance(player.ranking.global_ranking, int):
        try:
            globe = Image.open('assets/country_flags/globe2.png')
        except Exception:
            globe = Image.open('assets/country_flags/globe.png')
            size = 75, 75
            globe.thumbnail(size, Image.LANCZOS)
            globe.save('assets/country_flags/globe2.png', 'PNG')
            globe = Image.open('assets/country_flags/globe2.png')
        poster.paste(globe, (90, 340), globe.convert('RGBA'))
        draw.text(
            (165, 360),
            f'#{player.ranking.global_ranking}',
            fill=(255, 255, 255),
            font=font6,
        )

    if player.ranking.country_code is not None:
        try:
            globe = Image.open(f'assets/country_flags/{player.ranking.country_code.lower()}2.png')
        except Exception:
            globe = Image.open(f'assets/country_flags/{player.ranking.country_code.lower()}.png')
            size = 80, 80
            globe.thumbnail(size, Image.LANCZOS)
            globe.save(
                f'assets/country_flags/{player.ranking.country_code.lower()}2.png',
                'PNG',
            )
            globe = Image.open(f'assets/country_flags/{player.ranking.country_code.lower()}2.png')

        poster.paste(globe, (770, 350), globe.convert('RGBA'))
        if isinstance(player.ranking.local_ranking, int):
            draw.text(
                (870, 358),
                f'#{player.ranking.local_ranking}',
                fill=(255, 255, 255),
                font=font6,
            )
        else:
            draw.text(
                (870, 358),
                f'{player.ranking.country}',
                fill=(255, 255, 255),
                font=font6,
            )

    def save_im(poster):
        temp = io.BytesIO()
        poster = poster.resize((960, 540))
        poster.save(temp, format='PNG', optimize=True)
        temp.seek(0)
        file = disnake.File(fp=temp, filename="legends_poster.png")
        return file

    with concurrent.futures.ThreadPoolExecutor() as pool:
        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(pool, save_im, poster)

    return file


@register_button('legendhistory', parser='_:player')
async def legend_history(bot: CustomClient, player: coc.Player, embed_color: disnake.Color):
    player = await bot.ck_client.get_legend_player(player=player)
    results = await bot.history_db.find({'tag': player.tag}).sort('season', -1).to_list(length=None)
    if not results:
        embed = disnake.Embed(
            description=f'{player._.name} has never finished a season in legends',
            color=disnake.Color.red(),
        )
        return embed

    names = set()
    for result in results:
        names.add(result.get('name'))
    names = list(names)

    text = ''
    oldyear = '2015'
    embed = disnake.Embed(description='🏆= trophies, 🌎= global rank', color=embed_color)
    if names:
        names = ', '.join(names)
        embed.add_field(name='**Previous Names**', value=names, inline=False)
    for result in results:
        season = result.get('season')
        year = season.split('-')[0]
        month = season.split('-')[-1]
        month = calendar.month_name[int(month)]
        month = month.ljust(9)
        month = f'`{month}`'

        year = year[0:4]
        rank = result.get('rank')
        trophies = result.get('trophies')
        if year != oldyear:
            if text != '':
                embed.add_field(name=f'**{oldyear}**', value=text, inline=False)
            oldyear = year
            text = ''
        text += f'{month} | 🏆{trophies} | 🌎{rank}\n'

    if text != '':
        embed.add_field(name=f'**{oldyear}**', value=text, inline=False)
    embed.set_author(name=f'{player._.name} Legend History', icon_url=player.townhall.image_url)
    return embed


@register_button('legendclan', parser='_:clan')
async def legend_clan(bot: CustomClient, clan: Clan, embed_color: disnake.Color):
    players: List[LegendPlayer] = await bot.ck_client.get_clan_legend_players(clan=clan)
    players.sort(key=lambda x: x._.trophies, reverse=True)
    text = f'```#  Trph Off  Def  Name\n'

    for count, player in enumerate(players, 1):
        legend_day = player.get_legend_day()
        attack_text = f'{legend_day.attack_sum}{legend_day.num_attacks.superscript}'
        defense_text = f'{legend_day.defense_sum}{legend_day.num_defenses.superscript}'
        text += f'{count:<2} {player._.trophies} {attack_text:<4} {defense_text:<4} {player.clear_name[:13]}\n'
    text += '```'

    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f'{clan.name} Legends Overview', icon_url=clan.badge.url)
    embed.set_footer(text=gen_legend_date())
    return embed


@register_button('legendquick', parser='_:ctx:player', ephemeral=True, no_embed=True)
async def legend_quicksearch(bot: CustomClient, ctx: disnake.MessageInteraction, player: coc.Player):
    results = await bot.legend_profile.find_one({'discord_id': ctx.author.id})
    profile_tags = results.get('profile_tags', []) if results is not None else []
    tag = player.tag
    if tag in profile_tags:
        await bot.legend_profile.update_one(
            {'discord_id': ctx.author.id},
            {'$pull': {'profile_tags': tag, 'feed_tags': tag}},
            upsert=True,
        )
        await ctx.send(
            content=f'Removed {player.name} from your Quick Check & Daily Report list.',
            ephemeral=True,
        )
    elif len(profile_tags) >= 25:
        await ctx.send(
            content='Can only have 25 players on your Quick Check & Daily Report list. Please remove one.',
            ephemeral=True,
        )
    else:
        await bot.legend_profile.update_one({'discord_id': ctx.author.id}, {'$push': {'profile_tags': tag}}, upsert=True)
        await ctx.send(
            content=f'Added {player.name} to your Quick Check & Daily Report list.',
            ephemeral=True,
        )


@register_button('legendcutoff', parser='_:')
async def legend_cutoff(bot: CustomClient, embed_color: disnake.Color):
    results = (
        await bot.legend_rankings.find(
            {
                '$or': [
                    {'rank': 1},
                    {'rank': 5},
                    {'rank': 25},
                    {'rank': 50},
                    {'rank': 100},
                    {'rank': 200},
                    {'rank': 500},
                    {'rank': 1000},
                    {'rank': 2500},
                    {'rank': 5000},
                    {'rank': 10000},
                    {'rank': 25000},
                    {'rank': 50000},
                    {'rank': 100000},
                    {'rank': 250000},
                ]
            },
            projection={'rank': 1, 'trophies': 1},
        )
        .sort('rank', 1)
        .to_list(length=None)
    )
    text = ''
    for result in results:
        rank = f"#{result.get('rank')}"
        text += f"`{rank:>7} `{bot.emoji.trophy}`{result.get('trophies')}`\n"
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name='Legend Rank Cutoffs', icon_url=bot.fetch_emoji('Legend League').partial_emoji.url)
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


@register_button('legendstreaks', parser='_:limit')
async def legend_streaks(bot: CustomClient, limit: int, embed_color: disnake.Color):
    results = (
        await bot.player_stats.find({}, projection={'name': 1, 'legends.streak': 1}).sort('legends.streak', -1).limit(limit).to_list(length=None)
    )
    text = '``` # ★★★ Name\n'
    for count, result in enumerate(results, 1):
        text += f"{count:>2} {result.get('legends').get('streak'):>3} {result.get('name'):<15}\n"
    text += '```'
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(
        name='Legend Triple Streak Leaders',
        icon_url=bot.fetch_emoji('Legend League').partial_emoji.url,
    )
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


@register_button('legendbuckets', parser='_:')
async def legend_buckets(bot: CustomClient, embed_color: disnake.Color):
    pipeline = [
        {
            '$bucket': {
                'groupBy': '$trophies',
                'boundaries': [
                    4500,
                    4600,
                    4700,
                    4800,
                    4900,
                    5000,
                    5100,
                    5200,
                    5300,
                    5400,
                    5500,
                    5600,
                    5700,
                    5800,
                    5900,
                    6000,
                    6100,
                    6200,
                    6300,
                    6400,
                    6500,
                    8500,
                ],
                'output': {'count': {'$sum': 1}},
            }
        }
    ]
    results = await bot.legend_rankings.aggregate(pipeline=pipeline).to_list(length=None)
    text = '`  Troph Count    Perc`\n'
    lowest_rank = await bot.legend_rankings.find({}).sort([('rank', -1)]).limit(1).to_list(length=1)
    lowest_rank = lowest_rank[0].get('rank')
    for result in results:
        trophy = result.get('_id')
        if trophy == 6500:
            trophy = '6500+'
        mid_calc = (result.get('count') / lowest_rank) * 100
        perc_of_total = round(mid_calc, 3 if mid_calc < 1 else None)
        perc_of_total = str(perc_of_total).replace('0.', '.')
        if perc_of_total == '.0':
            perc_of_total = ''
        else:
            perc_of_total += '%'
        text += f"{bot.emoji.trophy}`{trophy:<5} {result.get('count'):<7} {perc_of_total:>5}`\n"
    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(
        name='Legend Trophy Buckets',
        icon_url=bot.fetch_emoji('Legend League').partial_emoji.url,
    )
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


@register_button('legendeosfinishers', parser='_:')
async def legend_eos_finishers(bot: CustomClient, embed_color: disnake.Color):
    results = await bot.history_db.find({'rank': 1}).sort('season', -1).limit(48).to_list(length=None)
    text = ''
    embed = disnake.Embed(color=embed_color)
    old_year = results[0].get('season').split('-')[0]
    for result in results:
        year = result.get('season').split('-')[0]
        month = calendar.month_name[int(result.get('season').split('-')[1])]
        name = result.get('name')
        trophies = result.get('trophies')
        if year != old_year:
            embed.add_field(name=old_year, value=text, inline=False)
            text = ''
            old_year = year
        text += f'`{month:>9} {trophies} \u200e{name}`\n'
    if text != '':
        embed.add_field(name=f'{old_year}', value=text, inline=False)
    embed.set_author(
        name='Legend EOS Finishers (last 4 years)',
        icon_url=bot.fetch_emoji('Legend League').partial_emoji.url,
    )
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed
