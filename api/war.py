from api.clan import BaseClan


class CWLRanking(BaseClan):
    def __init__(self, data: dict):
        super().__init__(data)
        self.season: str = data['season']
        self.league: str = data['league']
        self.rank: int = data['rank']
        self.name: str = data['name']
        self.stars: int = data['stars']
        self.destruction: float = round(data['destruction'], 2)
        self.rounds_won: dict = data['rounds']['won']
        self.rounds_tied: dict = data['rounds']['tied']
        self.rounds_lost: dict = data['rounds']['lost']


class CWLThreshold:
    def __init__(self, data: dict):
        self.id: str = data['id']
        self.name: str = data['name']
        self.promo: int = data['promo']
        self.demote: int = data['demote']
