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
        return f"{days} day(s) {hours} hrs {minutes} mins"
    elif diff < timedelta(hours=1):
        return f"{minutes} mins {seconds} secs"
    else:
        return f"{hours} hrs {minutes} mins"
