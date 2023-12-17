from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict

class PartialClan(BaseModel):
    name: str
    tag: str
    clanLevel: int
    role: str

class PartialBannedUser(BaseModel):
    tag: str = Field(validation_alias="VillageTag", serialization_alias="tag")
    date: str = Field(validation_alias="DateCreated", serialization_alias="date")
    notes: str = Field(validation_alias="Notes", serialization_alias="notes")
    added_by: int | None = Field(default=None)


class BannedUser(PartialBannedUser):
    name: str
    townhall: int
    share_link: str
    clan: PartialClan | None


class BannedResponse(BaseModel):
    items: List[BannedUser]