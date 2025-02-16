

class BaseLocation:
    def __init__(self, data: dict):
        self.code = data.get('country_code')
        self.name = data.get('country_name')


