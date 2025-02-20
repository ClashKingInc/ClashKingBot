from api.location import BaseLocation

class BasePlayer:
    def __init__(self, data: dict):
        self.tag: str = data['tag']



class LocationPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.country = BaseLocation(data=data)


class DonationPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.donated: int = data['donated']
        self.received: int = data['received']