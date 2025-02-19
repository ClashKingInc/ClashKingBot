

class BaseClan:
    def __init__(self, data: dict):
        self.tag = data['tag']


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