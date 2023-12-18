from .abc import BasicPlayer

class PartialClan():
    def __init__(self, data):
        self.name: str = data.get("name")
        self.tag: str = data.get("tag")
        self.clan_level: int = data.get("clanLevel")
        self.role: str = data.get("role")

class BannedUser(BasicPlayer):
    def __init__(self, data, client):
        super().__init__(data, client)
        self.date: str = data.get("date")
        self.notes: str = data.get("notes") if data.get("notes") != "" else "No Notes"
        self.added_by: int = data.get("added_by")
        self.clan: PartialClan | None = PartialClan(data=data.get("clan")) if data.get("clan") else None
        self.rollover_days: int | None = data.get("rollover_days")


class BannedResponse(BannedUser):
    def __init__(self, data, client):
        super().__init__(data, client)
        self.new_entry: bool = data.get("new_entry")



