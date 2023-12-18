from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

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
    rollover_days: int | None = Field(default=None)


class BannedUser(PartialBannedUser):
    name: str
    townhall: int
    share_link: str
    clan: PartialClan | None

class BanResponse(BannedUser):
    new_entry: bool


class BannedResponse(BaseModel):
    items: Optional[List[BannedUser]]


