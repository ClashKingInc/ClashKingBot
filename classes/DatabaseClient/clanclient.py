from .playerclient import PlayerClient


class ClanClient(PlayerClient):
    def __init__(self, bot):
        super().__init__(bot)
