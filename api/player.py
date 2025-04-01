from api.location import BaseLocation
from coc.abc import BaseClan

class BasePlayer:
    def __init__(self, data: dict):
        self.tag: str = data['tag']

class SortedPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.name: str = data['name']
        self.clan: BaseClan | None = BaseClan(data=data['clan'], client=None) if data['clan'] else None
        self.value: str | int = data['value']

class LocationPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.country = BaseLocation(data=data)


class DonationPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.donated: int = data['donated']
        self.received: int = data['received']


class SummaryPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.value: int = data['value']
        self.place: int = data['count']

class Summary:
    def __init__(self, items: list):
        data = {k: v for d in items for k, v in d.items()}
        self.gold: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['gold']]
        self.elixir: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['elixir']]
        self.dark_elixir: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['dark_elixir']]
        self.activity: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['activity']]
        self.attack_wins: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['attack_wins']]
        self.season_trophies: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['season_trophies']]
        self.troops_donated: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['donated']]
        self.troops_received: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['received']]
        self.capital_donated: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['capital_donated']]
        self.capital_raided: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['capital_raided']]
        self.war_stars: list[SummaryPlayer] = [SummaryPlayer(d) for d in data['war_stars']]


    @property
    def types(self):
        return self.__dict__.keys()

    def get_type(self, type: str) -> list[SummaryPlayer]:
        return self.__dict__[type]

    def as_list(self) -> list[tuple[str, list[SummaryPlayer]]]:
        return [(type, self.get_type(type)) for type in self.types]




