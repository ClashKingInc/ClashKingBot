from enum import Enum

class TrophySort(Enum):
    home = 0
    versus = 1
    capital = 2


class LinkParseTypes(Enum):
    army = "army"
    player = "player"
    clan = "clan"