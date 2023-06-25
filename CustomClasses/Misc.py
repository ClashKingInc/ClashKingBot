
class WarPlan():
    def __init__(self, data):
        self.name: str = data.get("name")
        self.player_tag: str = data.get("player_tag")
        self.townhall_level: int = data.get("townhall_level")
        self.notes = data.get("notes")
        self.stars = data.get("stars")
        self.targets = data.get("targets")
        self.map_position: int = data.get("map_position")

    @property
    def plan_text(self):
        if "-" in self.targets:
            return f"{self.stars}★ on Bases {self.targets}"
        else:
            return f"{self.stars}★ on Base {self.targets}"