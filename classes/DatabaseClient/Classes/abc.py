import coc
from utility.constants import SUPER_SCRIPTS, SHORT_CLAN_LINK, SHORT_PLAYER_LINK
from classes.emoji import EmojiType
from assets.emojiDictionary import emojiDictionary
from assets.thPicDictionary import thDictionary
import emoji
import re

class BasePlayer():
    def __init__(self, data: dict, api_player: coc.Player | coc.ClanMember):
        self.tag: str = data.get("tag")
        self.api_player = api_player
        self._ = api_player

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self._.name)
        name = re.sub('[*_`~/]', '', name)
        return f"\u200e{name}"

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace("#", "")

    @property
    def townhall(self):
        return CustomTownHall(level=self._.town_hall)

    @property
    def clan_name(self):
        try:
            clan_name = self._.clan.name
        except Exception:
            clan_name = "No Clan"
        return clan_name

    @property
    def clan_badge(self):
        try:
            clan_badge = self._.clan.badge.url
        except Exception:
            clan_badge = "https://clashking.b-cdn.net/unranked.png"
        return clan_badge


class BaseClan():
    def __init__(self, data: dict, api_clan: coc.Clan):
        self.tag: str = data.get("tag")
        self.api_clan = api_clan
        self._ = api_clan

    @property
    def clear_name(self):
        name = emoji.replace_emoji(self._.name)
        name = re.sub('[*_`~/]', '', name)
        return f"\u200e{name}"

    @property
    def share_link(self) -> str:
        return SHORT_PLAYER_LINK + self.tag.replace("#", "")



class CustomTownHall():
    def __init__(self, level):
        self._level = level if level >= 5 else 5

    def __str__(self):
        return str(self._level)

    def __int__(self):
        return self._level

    @property
    def emoji(self):
        return EmojiType(emojiDictionary(self.level))

    @property
    def image_url(self):
        return thDictionary(self._level)


class NumChoice():
    def __init__(self, num):
        self.integer = num if num <= 8 else 8

    def __int__(self):
        return self.integer

    def __str__(self):
        return str(self.integer)

    @property
    def superscript(self):
        return SUPER_SCRIPTS[self.integer]