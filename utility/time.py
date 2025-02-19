from datetime import datetime, timedelta
import pendulum as pend
import coc
import calendar

class DiscordTimeStamp:
    def __init__(self, date: pend.DateTime):
        self.slash_date = f'<t:{date.int_timestamp}:d>'
        self.text_date = f'<t:{date.int_timestamp}:D>'
        self.time_only = f'<t:{date.int_timestamp}:t>'
        self.full_date = f'<t:{date.int_timestamp}:F>'
        self.relative = f'<t:{date.int_timestamp}:R>'


def ts(date: pend.DateTime) -> DiscordTimeStamp:
    """
    Converts a Pendulum DateTime object into a DiscordTimeStamp object.

    :param date: A Pendulum DateTime object representing the date and time.
    :return: A DiscordTimeStamp object containing formatted Discord timestamp strings.
    """
    return DiscordTimeStamp(date=date)


def time_difference(start: datetime, end: datetime):
    # Calculate the difference
    diff = end - start

    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    seconds = diff.seconds % 60

    # Format output based on duration
    if days > 0:
        return f'{days} day(s) {hours} hrs {minutes} mins'
    elif diff < timedelta(hours=1):
        return f'{minutes} mins {seconds} secs'
    else:
        return f'{hours} hrs {minutes} mins'


def format_time(seconds):
    if seconds >= 3600:  # Convert to hours and minutes
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f'{hours} hr, {minutes} min' if minutes else f'{hours} hr'
    elif seconds >= 60:  # Convert to minutes and seconds
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f'{minutes} min, {remaining_seconds} sec' if remaining_seconds else f'{minutes} min'
    else:  # Just seconds
        return f'{seconds} sec'


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


def gen_raid_date():
    now = pend.now(tz=pend.UTC)
    current_dayofweek = now.day_of_week  # Monday = 0, Sunday = 6
    if (
        (current_dayofweek == 4 and now.hour >= 7)  # Friday after 7 AM UTC
        or (current_dayofweek == 5)  # Saturday
        or (current_dayofweek == 6)  # Sunday
        or (current_dayofweek == 0 and now.hour < 7)  # Monday before 7 AM UTC
    ):
        raid_date = now.subtract(days=(current_dayofweek - 4 if current_dayofweek >= 4 else 0)).date()
    else:
        forward = 4 - current_dayofweek  # Days until next Friday
        raid_date = now.add(days=forward).date()
    return str(raid_date)


def gen_season_date(num_seasons: int = 0, as_text: bool = True) -> str | list[str]:
    """
    Generates season dates based on the number of seasons ago.

    :param num_seasons: Number of seasons ago. Default is 0 (current season).
    :param as_text: If True, returns the date in "Month Year" format; otherwise, returns "YYYY-MM".
    :return: A single date string if num_seasons is 0, otherwise a list of date strings.
    """

    def format_date(date: pend.DateTime, text_format: bool) -> str:
        return f'{calendar.month_name[date.month]} {date.year}' if text_format else date.format('YYYY-MM')

    end_date = pend.instance(coc.utils.get_season_end().replace(tzinfo=pend.UTC))

    if num_seasons == 0:
        return format_date(end_date, as_text)

    return [format_date(end_date.subtract(months=i), as_text) for i in range(num_seasons + 1)]


def gen_legend_date():
    now = pend.now(tz=pend.UTC)
    date = now.subtract(days=1).date() if now.hour < 5 else now.date()
    return str(date)


def gen_games_season():
    now = pend.now(tz=pend.UTC)
    month = f'{now.month:02}'  # Ensure two-digit month
    return f'{now.year}-{month}'


def is_raids():
    """
    Check if the current time is within the raid tracking window (Friday 7:00 UTC to Monday 7:00 UTC).
    """
    now = pend.now(tz=pend.UTC)
    friday_7am = now.start_of('week').add(days=4, hours=7)
    monday_7am = now.start_of('week').add(days=7, hours=7)
    return friday_7am <= now < monday_7am


def is_cwl():
    now = pend.now(tz=pend.UTC)
    return 1 <= now.day <= 10 and not ((now.day == 1 and now.hour < 8) or (now.day == 11 and now.hour >= 8))


def is_clan_games():
    now = pend.now(tz=pend.UTC)
    start = now.start_of('month').add(days=21, hours=8)  # 22nd at 08:00 UTC
    end = now.start_of('month').add(days=27, hours=8)  # 28th at 08:00 UTC
    return start <= now < end


def season_start_end(season: str, gold_pass_season: bool = False):
    """
    Generate the season start end that is used for gold pass and clan games
    :param season: a season in the format YYYY-MM
    :param gold_pass_season: True if you want the season that the gold pass & clan games use
    """
    year = int(season[:4])
    month = int(season[-2:])

    if not gold_pass_season:
        prev_month = 12 if month == 1 else month - 1
        prev_year = year - 1 if month == 1 else year

        season_start = pend.from_timestamp(
            coc.utils.get_season_start(month=prev_month, year=prev_year).timestamp(), tz='UTC'
        )
        season_end = pend.from_timestamp(
            coc.utils.get_season_end(month=prev_month, year=prev_year).timestamp(), tz='UTC'
        )
    else:
        season_start = pend.datetime(year, month, 1, tz='UTC')  # First day of the month
        season_end = season_start.add(months=1)  # First day of the next month

    return season_start, season_end
