from coc.abc import BaseClan

from api.location import BaseLocation


class BasePlayer:
    def __init__(self, data: dict):
        self.tag: str = data['tag']


class Player(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.name: str = data['name']


class SortedPlayer(Player):
    def __init__(self, data: dict):
        super().__init__(data)
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


class WarStatsPlayer(Player):
    def __init__(self, data: dict):
        super().__init__(data)
        self.townhall: int = data['townhall']

        self.__missed_data = {'missed_hits': data.get('missed', {}).get('all', 0)}
        self.__data = data.get('stats', {}) | self.__missed_data

        self.attacks: int = self.__data.get('attacks', 0)
        self.destruction: int = self.__data.get('destruction', 0)
        self.stars: int = self.__data.get('stars', 0)
        self.fresh: int = self.__data.get('fresh', 0)
        self.won: int = self.__data.get('won', 0)
        self.duration: int = self.__data.get('duration', 0)
        self.order: int = self.__data.get('order', 0)
        self.avg_destruction: float = self.__data.get('avg_destruction', 0.0)
        self.avg_stars: float = self.__data.get('avg_stars', 0.0)
        self.avg_duration: float = self.__data.get('avg_duration', 0.0)
        self.avg_order: float = self.__data.get('avg_order', 0.0)
        self.avg_fresh: float = self.__data.get('avg_fresh', 0.0)
        self.avg_won: float = self.__data.get('avg_won', 0.0)
        self.zero_stars: int = self.__data.get('zero_stars', 0)
        self.one_stars: int = self.__data.get('one_stars', 0)
        self.two_stars: int = self.__data.get('two_stars', 0)
        self.three_stars: int = self.__data.get('three_stars', 0)
        self.avg_zero_stars: float = self.__data.get('avg_zero_stars', 0.0)
        self.avg_one_stars: float = self.__data.get('avg_one_stars', 0.0)
        self.avg_two_stars: float = self.__data.get('avg_two_stars', 0.0)
        self.avg_three_stars: float = self.__data.get('avg_three_stars', 0.0)
        self.missed_hits: int = self.__data.get('missed_hits', 0)
        self.avg_defender_position: float = self.__data.get('avg_defender_position', 0.0)
