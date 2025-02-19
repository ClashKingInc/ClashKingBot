from api.location import BaseLocation

class BasePlayer:
    def __init__(self, data: dict):
        self.tag = data['tag']



class LocationPlayer(BasePlayer):
    def __init__(self, data: dict):
        super().__init__(data)
        self.country = BaseLocation(data=data)