import emoji
from toolbox.strings import MarkdownFormat, remove_markdown
from wcwidth import wcwidth

from utility.constants import SUPER_SCRIPTS


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


def create_superscript(num):
    digits = [int(num) for num in str(num)]
    new_num = ''
    for d in digits:
        new_num += SUPER_SCRIPTS[d]

    print(new_num)
    return new_num


def truncate_display_width(text: str, max_width: int, remove_emojis: bool = False) -> str:
    if remove_emojis:
        text = emoji.replace_emoji(text)

    text = remove_markdown(text, MarkdownFormat.ALL)
    text = text.replace('`', '')
    result = ''
    width = 0
    for char in text:
        char_width = wcwidth(char)
        if width + char_width > max_width:
            break
        result += char
        width += char_width
    return result


def fmt(value, fmt: str, suppress_100: bool = False, suffix: str = '') -> str:
    if suppress_100 and isinstance(value, (int, float)) and round(value, 1) == 100:
        import re

        match = re.match(r'[<>=^]?(\d+)', fmt)
        width = int(match.group(1)) if match else 0
        align = fmt[0] if fmt[0] in '<>^=' else ''
        return f'{int(value):{align}{width}}' + suffix
    return f'{format(value, fmt)}{suffix}'


async def safe_run(func, **kwargs):
    try:
        await func(**kwargs)
    except Exception:
        pass
