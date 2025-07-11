from pymongo import AsyncMongoClient


class MongoClient(AsyncMongoClient):
    def __init__(self, uri: str, **kwargs):
        super().__init__(host=uri, **kwargs)
        self.__clashking = self.get_database('clashking')
        self.button_store = self.__clashking.get_collection('button_store')
