from typing import List, Optional, Type

import coc
import pendulum as pend
from aiocache import SimpleMemoryCache, cached
from coc import Clan, ClanWar, Location, Player, WarRound

from .clan import CustomClan
from .player import BasePlayer


class CustomClashClient(coc.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get_player(self, player_tag: str, cls: Type[Player] = BasePlayer, **kwargs) -> Player:
        player_tag = player_tag.split('|')[-1]

        return await super().get_player(player_tag, cls, **kwargs)

    async def get_clan(self, tag: str, cls: Type[Clan] = CustomClan, **kwargs) -> Clan:
        tag = tag.split('|')[-1]

        return await super().get_clan(tag, cls, **kwargs)

    async def get_current_war(
        self, clan_tag: str, cwl_round: WarRound = WarRound.current_war, cls: Type[ClanWar] = None, **kwargs
    ) -> Optional[ClanWar]:
        try:
            war = await super().get_current_war(clan_tag, cwl_round, cls, **kwargs)
            if war.state == 'notInWar':
                return None
        except coc.PrivateWarLog:
            result = (
                await self.clan_wars.find(
                    {
                        '$and': [
                            {'clans': clan_tag},
                            {'custom_id': None},
                            {'endTime': {'$gte': pend.now(tz=pend.UTC).int_timestamp}},
                        ]
                    }
                )
                .sort({'endTime': -1})
                .to_list(length=None)
            )
            if not result:
                return None
            result = result[0]
            clans: list = result.get('clans', [])
            clans.remove(clan_tag)
            clan_to_use = clans[0]

            war = await self.get_current_war(clan_tag=clan_to_use)
            return war

    @cached(ttl=None, cache=SimpleMemoryCache)
    async def search_locations(
        self, *, limit: int = None, before: str = None, after: str = None, cls: Type[Location] = None, **kwargs
    ) -> List[Location]:
        return await super().search_locations(limit=limit, before=before, after=after, cls=cls, **kwargs)

    async def fetch_players(
        self, player_tags: list[str], cls: Type[Player] = BasePlayer, cache: bool = ..., **kwargs
    ) -> list[Player]:
        pass

    async def fetch_clans(self, clan_tags: list[str]):
        pass
        self.season_start_end()
