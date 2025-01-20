import re

import coc
import emoji

from classes.cocpy.other import CustomTownHall
from utility.constants import SHORT_PLAYER_LINK


class BasePlayer(coc.Player):
    def __init__(self, *, data, client, **kwargs):
        super().__init__(data=data, client=client, **kwargs)
        self.extra = kwargs.pop('extra', None)

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self.name)
        name = re.sub('[*_`~/]', '', name)
        return f'\u200e{name}'

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace('#', '')

    @property
    def townhall(self):
        return CustomTownHall(level=self.town_hall)

    @property
    def clan_name(self):
        return self.clan.name if self.clan else 'No Clan'

    @property
    def clan_badge(self):
        return self.clan.badge.url if self.clan else 'https://clashking.b-cdn.net/unranked.png'






