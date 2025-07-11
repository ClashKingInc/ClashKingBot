class BaseLocation:
    def __init__(self, data: dict):
        self.code = data.get('country_code')
        self.name = data.get('country_name')

    def __eq__(self, other):
        if not isinstance(other, BaseLocation):
            return False
        return self.code == other.code

    def __hash__(self):
        return hash(self.code)

    def __repr__(self):
        return f'BaseLocation(code={self.code!r}, name={self.name!r})'


class ClanRanking(BaseLocation):
    def __init__(self, data: dict):
        super().__init__(data)
        self.tag = data['tag']
        self.global_rank: int | None = data['global_rank']
        self.local_rank: int | None = data['local_rank']
