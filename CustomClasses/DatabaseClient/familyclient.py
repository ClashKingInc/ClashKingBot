
from .clanclient import ClanClient
import coc
from Exceptions.CustomExceptions import NoLegendStatsFound


class FamilyClient(ClanClient):
    def __init__(self, bot):
        super().__init__(bot)



