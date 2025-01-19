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


def get_clan_member_tags(clans: List[coc.Clan]) -> List[str]:
    clan_member_tags = []
    for clan in clans:
        for member in clan.members:
            clan_member_tags.append(member.tag)
    return clan_member_tags


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


async def safe_run(func: Callable, **kwargs):
    try:
        await func(**kwargs)
    except Exception:
        pass
