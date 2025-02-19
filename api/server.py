
from typing import TYPE_CHECKING, List, Union

import coc
import disnake


from coc import utils


class ServerSettings():
    def __init__(self, data: dict):
        self._data = data
        self.server_id = data.get('server')
        self.embed_color = disnake.Color(data.get('embed_color', 0x2ECC71))


class ServerClanSettings:
    def __init__(self, data: dict):
        self.name = data.get('name')
        self.tag = data.get('tag')
        self.server_id = data.get('server')

        self.category = data.get('category')








