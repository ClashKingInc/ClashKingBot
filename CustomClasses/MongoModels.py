from typing import Optional, List

from odmantic import Field, Model, EmbeddedModel

class EditedBy(EmbeddedModel):
    discord_name: str
    discord_id: int

class Plans(EmbeddedModel):
    name: str
    player_tag: str
    townhall_level: int
    notes: Optional[str] = None
    stars: Optional[str] = None
    targets: Optional[str] = None
    map_position: int

    @property
    def plan_text(self):
        if "-" in self.targets:
            return f"{self.stars}★ on Bases {self.targets}"
        else:
            return f"{self.stars}★ on Base {self.targets}"

class Lineups(Model):
    server_id: int
    clan_tag: str
    edited_by: Optional[List[EditedBy]] = []
    plans: Optional[List[Plans]] = []
