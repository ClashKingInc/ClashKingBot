import coc

from exceptions.CustomExceptions import NoLegendStatsFound

from .clanclient import ClanClient


class FamilyClient(ClanClient):
    def __init__(self, bot):
        super().__init__(bot)
