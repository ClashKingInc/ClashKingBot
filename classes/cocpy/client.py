from typing import Type

import coc
from coc import Player


class CustomClashClient(coc.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get_player(self, player_tag: str, cls: Type[Player] = Player, **kwargs) -> Player:
        player_tag = player_tag.split('|')[-1]



    async def fetch_players(self, player_tags: list[str]):
        pass

    async def fetch_clans(self, clan_tags: list[str]):
        pass