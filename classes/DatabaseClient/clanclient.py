from .playerclient import PlayerClient
import coc
from exceptions.CustomExceptions import MessageException


class ClanClient(PlayerClient):
    def __init__(self, bot):
        super().__init__(bot)
