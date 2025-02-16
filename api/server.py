
from typing import TYPE_CHECKING, List, Union

import coc
import disnake

from utility.constants import AUTOREFRESH_TRIGGERS, ROLE_TREATMENT_TYPES



from coc import utils


class ServerSettings():
    def __init__(self, data: dict):
        self._data = data
        self.server_id = data.get('server')
        self.embed_color = disnake.Color(data.get('embed_color', 0x2ECC71))





