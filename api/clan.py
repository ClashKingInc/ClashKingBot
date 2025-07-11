import coc


class BaseClan:
    def __init__(self, data: dict):
        self.tag = data['tag']


class BasicClan(BaseClan):
    def __init__(self, data: dict):
        super().__init__(data)
        self.name = data['name']


class ClanTotals(BaseClan):
    def __init__(self, data: dict):
        super().__init__(data)
        self._raw_data = data
        self.tracked_player_count: int = data['tracked_player_count']
        self.clan_games_points: int = data['clan_games_points']
        self.troops_donated: int = data['troops_donated']
        self.troops_received: int = data['troops_received']
        self.clan_capital_donated: int = data['clan_capital_donated']
        self.activity_per_day: int = data['activity']['per_day']
        self.activity_last_48h: int = data['activity']['last_48h']
        self.activity_score: int = data['activity']['score']


class ClanCompo:
    def __init__(self, data: dict):
        self._data = data
        self.townhall: dict = data['townhall']
        self.trophies: dict = data['trophies']
        self.location: dict = data['location']
        self.role: dict = data['role']
        self.league: dict = data['league']
        self.country_map: dict = data['country_map']
        self.total_members: int = data['total_members']
        self.clan_count: int = data['clan_count']

    @property
    def clan(self) -> coc.Clan | None:
        if self._data.get('clan'):
            return coc.Clan(data=self._data['clan'], client=None)
        return None
