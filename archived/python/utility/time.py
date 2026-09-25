from datetime import datetime, timedelta


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
