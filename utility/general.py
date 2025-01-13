import calendar
import datetime as dt
import io
import random
from datetime import datetime
from typing import Callable, List

import aiohttp
import coc
import disnake
import pendulum as pend
from coc import utils
from expiring_dict import ExpiringDict
from pytz import utc

from utility.clash.other import league_to_emoji
from utility.constants import SUPER_SCRIPTS, placeholders, war_leagues


IMAGE_CACHE = ExpiringDict()


async def fetch(url, session, **kwargs):
    async with session.get(url) as response:
        if kwargs.get('extra') is not None:
            return [(await response.json()), kwargs.get('extra')]
        else:
            return await response.json()


def create_superscript(num):
    digits = [int(num) for num in str(num)]
    new_num = ''
    for d in digits:
        new_num += SUPER_SCRIPTS[d]

    return new_num


async def calculate_time(type, war: coc.ClanWar = None):
    text = ''
    now = datetime.utcnow().replace(tzinfo=utc)
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    if type == 'CWL':
        is_cwl = True
        if day == 1:
            first = datetime(year, month, 1, hour=8, tzinfo=utc)
        else:
            if month + 1 == 13:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month + 1
                next_year = year
            first = datetime(next_year, next_month, 1, hour=8, tzinfo=utc)
        end = datetime(year, month, 11, hour=8, tzinfo=utc)
        if day >= 1 and day <= 10:
            if (day == 1 and hour < 8) or (day == 11 and hour >= 8):
                is_cwl = False
            else:
                is_cwl = True
        else:
            is_cwl = False

        if is_cwl:
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'ends {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'ends in {int(mins)}M'
            else:
                text = f'ends {int(days)}D {int(hrs)}H'
        else:
            time_left = first - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'in {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'in {int(mins)}M'
            else:
                text = f'in {int(days)}D {int(hrs)}H'

    elif type == 'Clan Games':
        is_games = True
        first = datetime(year, month, 22, hour=8, tzinfo=utc)
        end = datetime(year, month, 28, hour=8, tzinfo=utc)
        if day >= 22 and day <= 28:
            if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
                is_games = False
            else:
                is_games = True
        else:
            is_games = False

        if day == 28 and hour >= 8:
            if month + 1 == 13:
                next_month = 1
                year += 1
            else:
                next_month = month + 1
            first = datetime(year, next_month, 22, hour=8, tzinfo=utc)

        if day >= 29:
            if month + 1 == 13:
                next_month = 1
                year += 1
            else:
                next_month = month + 1
            first = datetime(year, next_month, 22, hour=8, tzinfo=utc)

        if is_games:
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'ends {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'ends in {int(mins)}M'
            else:
                text = f'ends {int(days)}D {int(hrs)}H'
        else:
            time_left = first - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'in {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'in {int(mins)}M'
            else:
                text = f'in {int(days)}D {int(hrs)}H'

    elif type == 'Raid Weekend':

        now = datetime.utcnow().replace(tzinfo=utc)
        current_dayofweek = now.weekday()
        if (
            (current_dayofweek == 4 and now.hour >= 7)
            or (current_dayofweek == 5)
            or (current_dayofweek == 6)
            or (current_dayofweek == 0 and now.hour < 7)
        ):
            if current_dayofweek == 0:
                current_dayofweek = 7
            is_raids = True
        else:
            is_raids = False

        if is_raids:
            end = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(7 - current_dayofweek))
            time_left = end - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'end {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'end in {int(mins)}M'
            else:
                text = f'end {int(days)}D {int(hrs)}H'
        else:
            first = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(4 - current_dayofweek))
            time_left = first - now
            secs = time_left.total_seconds()
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(days) == 0:
                text = f'in {int(hrs)}H {int(mins)}M'
                if int(hrs) == 0:
                    text = f'in {int(mins)}M'
            else:
                text = f'in {int(days)}D {int(hrs)}H'

    elif type == 'EOS':
        end = utils.get_season_end().replace(tzinfo=utc)
        time_left = end - now
        secs = time_left.total_seconds()
        days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
        hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
        mins, secs = divmod(secs, secs_per_min := 60)

        if int(days) == 0:
            text = f'in {int(hrs)}H {int(mins)}M'
            if int(hrs) == 0:
                text = f'in {int(mins)}M'
        else:
            text = f'in {int(days)}D {int(hrs)}H '

    elif type == 'Season Day':
        start = utils.get_season_start().replace(tzinfo=utc)
        end = utils.get_season_end().replace(tzinfo=utc)

        start_pendulum = pend.instance(start)
        end_pendulum = pend.instance(end)
        now = pend.now('UTC')

        days_since_start = now.diff(start_pendulum).in_days()
        days_from_start_to_end = start_pendulum.diff(end_pendulum).in_days()

        text = f'{days_since_start}/{days_from_start_to_end}'

    elif type == 'War Score':
        if war is None:
            text = 'Not in War'
        elif str(war.state) == 'preparation':
            secs = war.start_time.seconds_until
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if int(hrs) == 0:
                text = f'in {mins}M'
            else:
                text = f'{hrs}H {mins}M'
        else:
            text = f'{war.clan.stars}⭐| {war.opponent.stars}⭐'

    elif type == 'War Timer':
        if war is None:
            text = 'Not in War'
        else:
            secs = war.end_time.seconds_until
            days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
            hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
            mins, secs = divmod(secs, secs_per_min := 60)
            if days != 0:
                text = f'{days}D {hrs}H'
            elif int(hrs) == 0:
                text = f'in {mins}M'
            else:
                text = f'{hrs}H {mins}M'

    return text


def get_clan_member_tags(clans: List[coc.Clan]) -> List[str]:
    clan_member_tags = []
    for clan in clans:
        for member in clan.members:
            clan_member_tags.append(member.tag)
    return clan_member_tags


def response_to_line(bot, response, clan):
    clans = response['clans']
    season = response['season']
    tags = [x['tag'] for x in clans]
    stars = {}
    for tag in tags:
        stars[tag] = 0
    rounds = response['rounds']
    for round in rounds:
        wars = round['wars']
        for war in wars:
            main_stars = war['clan']['stars']
            main_destruction = war['clan']['destructionPercentage']
            stars[war['clan']['tag']] += main_stars

            opp_stars = war['opponent']['stars']
            opp_destruction = war['opponent']['destructionPercentage']
            stars[war['opponent']['tag']] += opp_stars

            if main_stars > opp_stars:
                stars[war['clan']['tag']] += 10
            elif opp_stars > main_stars:
                stars[war['opponent']['tag']] += 10
            elif main_destruction > opp_destruction:
                stars[war['clan']['tag']] += 10
            elif opp_destruction > main_destruction:
                stars[war['opponent']['tag']] += 10
    stars = dict(sorted(stars.items(), key=lambda item: item[1], reverse=True))
    place = list(stars.keys()).index(clan.tag) + 1
    league = response['leagueId']
    league_name = [x['name'] for x in war_leagues['items'] if x['id'] == league][0]
    promo = [x['promo'] for x in war_leagues['items'] if x['id'] == league][0]
    demo = [x['demote'] for x in war_leagues['items'] if x['id'] == league][0]

    if place <= promo:
        emoji = '<:warwon:932212939899949176>'
    elif place >= demo:
        emoji = '<:warlost:932212154164183081>'
    else:
        emoji = '<:dash:933150462818021437>'

    end = 'th'
    ends = {1: 'st', 2: 'nd', 3: 'rd'}
    if place <= 3:
        end = ends[place]

    year = season[0:4]
    month = season[5:]
    month = calendar.month_abbr[int(month)]
    # month = month.ljust(9)
    date = f'`{month}`'
    league = str(league_name).replace('League ', '')
    league = league.ljust(14)
    league = f'{league}'

    tier = str(league_name).count('I')

    return (
        f'{emoji} {league_to_emoji(bot=bot, league=league_name)}{SUPER_SCRIPTS[tier]} `{place}{end}` | {date}\n',
        year,
    )


def notate_number(number: int, zero=False):
    if number == 0 and not zero:
        return ''
    if number / 1000000 >= 1:
        rounded = round(number / 1000000, 1)
        if len(str(rounded)) >= 4:
            rounded = round(number / 1000000, None)
        return f'{rounded}M'
    elif number / 1000 >= 1:
        rounded = round(number / 1000, 1)
        if len(str(rounded)) >= 4:
            rounded = round(number / 1000, None)
        return f'{rounded}K'
    else:
        return number


def custom_round(number: int, add_percent=None):
    number = round(number, 1)
    if len(str(number)) <= 3:
        number = format(number, '.2f')
    elif number == 100.0:
        number = 100
    if add_percent:
        return f'{number}%'
    return number


def convert_seconds(seconds):
    if seconds is None:
        return 'N/A'
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return '%d:%02d:%02d' % (hour, minutes, seconds)


def smart_convert_seconds(seconds, granularity=2):
    intervals = (
        ('w', 604800),  # 60 * 60 * 24 * 7
        ('d', 86400),  # 60 * 60 * 24
        ('h', 3600),  # 60 * 60
        ('m', 60),
    )

    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append('{}{}'.format(int(value), name))
    return ' '.join(result[:granularity])


async def download_image(url: str):
    cached = IMAGE_CACHE.get(url)
    if cached is None:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                image_data = await response.read()
            await session.close()
        image_bytes: bytes = image_data
        IMAGE_CACHE.ttl(url, image_bytes, 3600 * 4)
    else:
        image_bytes = cached
    return io.BytesIO(image_bytes)


def acronym(stng):
    # add first letter
    oupt = stng[0]

    # iterate over string
    for i in range(1, len(stng)):
        if stng[i - 1] == ' ':
            # add letter next to space
            oupt += stng[i]

    # uppercase oupt
    oupt = oupt.upper()
    return oupt


def get_guild_icon(guild: disnake.Guild | None):
    if guild is None:
        icon = None
    else:
        icon = guild.icon
    if icon is None:
        return random.choice(placeholders)
    return icon.url


async def safe_run(func: Callable, **kwargs):
    try:
        await func(**kwargs)
    except Exception:
        pass

async def shorten_link(url: str):
    api_url = 'https://api.clashk.ing/shortner'
    params = {'url': url}
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('url')
            else:
                return None
