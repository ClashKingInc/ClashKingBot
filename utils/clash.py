import os
import coc
from datetime import datetime
from datetime import timedelta
import datetime as dt
import pytz
utc = pytz.utc

from dotenv import load_dotenv
load_dotenv()

COC_EMAIL = os.getenv("COC_EMAIL")
COC_PASSWORD = os.getenv("COC_PASSWORD")
DB_LOGIN = os.getenv("DB_LOGIN")
LINK_API_USER = os.getenv("LINK_API_USER")
LINK_API_PW = os.getenv("LINK_API_PW")

from disnake import utils

import certifi
ca = certifi.where()

import motor.motor_asyncio
client = motor.motor_asyncio.AsyncIOMotorClient(DB_LOGIN)
import disnake

def create_weekends():
    return ["Last Week", "Two Weeks Ago", "Last 4 Weeks (all)", "Last 8 Weeks (all)"]

def create_weekend_list(option, weeks=4):
    weekends = []
    for x in range(weeks):
        now = datetime.utcnow().replace(tzinfo=utc)
        now = now - timedelta(x * 7)
        current_dayofweek = now.weekday()
        if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
                current_dayofweek == 0 and now.hour < 7):
            if current_dayofweek == 0:
                current_dayofweek = 7
            fallback = current_dayofweek - 4
            raidDate = (now - timedelta(fallback)).date()
        else:
            forward = 4 - current_dayofweek
            raidDate = (now + timedelta(forward)).date()
        weekends.append(str(raidDate))

    if option == "Current Week":
        return [weekends[0]]
    elif option == "Last Week":
        return [weekends[1]]
    else:
        return weekends[0:weeks]


def weekend_timestamps():
    weekends = []
    for x in range(-1, 8):
        now = datetime.utcnow()
        now = now - timedelta(x * 7)
        year = now.year
        month = now.month
        day = now.day
        hour = now.hour
        current_dayofweek = now.weekday()
        if current_dayofweek == 0 and hour < 7:
            now = now - timedelta(days=1)
            year = now.year
            month = now.month
            day = now.day
            hour = now.hour
            current_dayofweek = now.weekday()
        #end = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(7 - current_dayofweek))
        first = datetime(year, month, day, hour=7, tzinfo=utc) + dt.timedelta(days=(4 - current_dayofweek))
        weekends.append(int(first.timestamp()))
    return weekends
