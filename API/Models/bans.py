from pydantic import BaseModel, Field, validator


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
        allow_population_by_field_name = True