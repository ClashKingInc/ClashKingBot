
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class ServerSettings(BaseModel):
    server_id: int = Field(validation_alias="server")
    banlist_channel: int = Field(validation_alias="banlist", default=None)
    leadership_eval: bool = Field(validation_alias="leadership_eval", default=True)
