import coc
import disnake


class CustomClan():
    def __init__(self, data: dict, clan: coc.Clan = None):
        self.data = data
        self.clan = clan


class BanEntry():
    def __init__(self, data: dict):
        self.data = data
        self.player_tag = data.get("VillageTag")
        self.player_name = data.get("VillageName")

    @property
    def date_created(self):
        date = self.data.get("DateCreated")


