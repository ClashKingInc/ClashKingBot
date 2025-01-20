class BaseClan:
    def __init__(self, data: dict, api_clan: coc.Clan):
        self.tag: str = data.get('tag')
        self.api_clan = api_clan
        self._ = api_clan

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self._.name)
        name = re.sub('[*_`~/]', '', name)
        return f'\u200e{name}'

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace('#', '')


class CustomTownHall:
    def __init__(self, level):
        self._level = level

    def __str__(self):
        return str(self._level)

    def __int__(self):
        return self._level

    @property
    def image_url(self):
        return f'https://assets.clashk.ing/home-base/town-hall-pics/town-hall-{self._level}.png'


class NumChoice:
    def __init__(self, num):
        self.integer = num if num <= 8 else 8

    def __int__(self):
        return self.integer

    def __str__(self):
        return str(self.integer)

    @property
    def superscript(self):
        return SUPER_SCRIPTS[self.integer]