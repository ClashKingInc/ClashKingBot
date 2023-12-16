from pydantic import BaseModel, Field, validator, RootModel
from typing import List, Dict

class BannedUser(BaseModel):
    name: str
    townhall: int
    share_link: str
    clan: dict | None
    VillageTag: str = Field(alias="tag")
    DateCreated: str = Field(alias="date")
    Notes: str = Field(alias="notes")
    added_by: int = Field(default=824653933347209227)


    class Config:
        populate_by_name = True


class BannedResponse(BaseModel):
    items: List[BannedUser]