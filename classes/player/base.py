import coc
import emoji
import re

from ..DatabaseClient.Classes.abc import CustomTownHall
from utility.constants import SHORT_PLAYER_LINK

# these are attributes that every custom player should have
class BasePlayer:
    def __init__(self, data: dict, api_player: coc.Player | coc.ClanMember):
        self.tag: str = data.get('tag')
        self.api_player = api_player
        self._ = api_player

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self._.name)
        name = re.sub('[*_`~/]', '', name)
        return f'\u200e{name}'

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace('#', '')

    @property
    def townhall(self):
        return CustomTownHall(level=self._.town_hall)

    @property
    def clan_name(self):
        try:
            clan_name = self._.clan.name
        except Exception:
            clan_name = 'No Clan'
        return clan_name

    @property
    def clan_badge(self):
        try:
            clan_badge = self._.clan.badge.url
        except Exception:
            clan_badge = 'https://clashking.b-cdn.net/unranked.png'
        return clan_badge
