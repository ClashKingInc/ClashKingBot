import coc

from exceptions.CustomExceptions import MessageException

from .playerclient import PlayerClient


class ClanClient(PlayerClient):
    def __init__(self, bot):
        super().__init__(bot)
