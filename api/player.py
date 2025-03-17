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