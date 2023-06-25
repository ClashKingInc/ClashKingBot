from pydantic import BaseModel
from typing import List, Dict, Union, Any


class PlayerClan(BaseModel):
    tag: str
    clanLevel: int
    name: str
    badgeUrls: dict


class DonationSeasons(Dict):
    received: int
    donated: int


class LegendDays(Dict):
    num_attacks: int
    attacks: List
    defenses: List


class Player(BaseModel):
    tag: str
    name: str
    clan_tag: Union[str, None] = None
    league: Union[str, None] = None
    last_online: Union[int, None] = 0
    last_online_times: Union[Dict, None] = {}
    donations: Union[DonationSeasons, None] = {}
    legends: Union[LegendDays, None] = {}
    capital_gold: Union[Dict, None] = {}
    clan_games: Union[Dict, None] = {}
    gold_looted: Union[Dict, None] = {}
    elixir_looted: Union[Dict, None] = {}
    dark_elixir_looted: Union[Dict, None] = {}
    historical_data: Any
    war_hits: Union[List, None] = []
