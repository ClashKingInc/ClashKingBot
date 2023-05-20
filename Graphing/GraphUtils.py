from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient

import pandas as pd
from typing import TYPE_CHECKING, List, Union, Any, Optional, Dict

import aiohttp
import os
if TYPE_CHECKING:
    from Graphing import GraphCog
    graphcog = GraphCog.GraphCog
else:
    graphcog = commands.Cog

LEAGUES = ["Legend League", "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]
import json

class GraphUtils(graphcog):
    _BASE_URL = "https://api.datawrapper.de"
    _CHARTS_URL = _BASE_URL + "/v3/charts"
    _PUBLISH_URL = _BASE_URL + "/charts"
    _FOLDERS_URL = _BASE_URL + "/folders"
    _access_token = os.getenv("DATAWRAPPER_TOKEN")
    _auth_header = {"Authorization": f"Bearer {_access_token}"}

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def create_and_publish_chart(
            self,
            server_id: int,
            season: str,
            gtype: str,
            title: str = "New Chart",
            chart_type: str = "d3-bars-stacked",
            data: Union[pd.DataFrame, None] = None,
            folder_id: str = "",
            metadata: Optional[Dict[Any, Any]] = None,
    ) -> Union[Dict[Any, Any], None, Any]:
        """Creates a new Datawrapper chart, table or map.
        You can pass a pandas DataFrame as a `data` argument to upload data.
        Returns the created chart's information.

        Parameters
        ----------
        title : str, optional
            Title for new chart, table or map, by default "New Chart"
        chart_type : str, optional
            Chart type to be created. See https://developer.datawrapper.de/docs/chart-types, by default "d3-bars-stacked"
        data : [type], optional
            A pandas DataFrame containing the data to be added, by default None
        folder_id : str, optional
            ID of folder in Datawrapper.de for the chart, table or map to be created in, by default ""
        metadata: dict, optional
            A Python dictionary of properties to add.

        Returns
        -------
        dict
            A dictionary containing the created chart's information.
        """

        _header = self._auth_header
        _header["content-type"] = "application/json"
        _data = {"title": title, "type": chart_type}

        if folder_id:
            _data["folderId"] = folder_id
        if metadata:
            _data["metadata"] = metadata  # type: ignore

        chart_id = await self.bot.server_db.find_one({"server" : server_id})
        if chart_id is not None:
            chart_id = chart_id.get(f"{gtype}-{season}-chart_id")

        was_none = False
        if chart_id is None:
            was_none = True
            async with aiohttp.ClientSession(headers=_header) as session:
                async with session.post(url=self._CHARTS_URL, data=json.dumps(_data)) as new_chart_response:
                    if new_chart_response.status <= 201:
                        chart_info = await new_chart_response.json()
                        chart_id = chart_info['publicId']
                        await self.bot.server_db.update_one({"server" : server_id}, {"$set" : {f"{gtype}-{season}-chart_id" : chart_id}})
                    await session.close()

        _header["content-type"] = "text/csv"
        async with aiohttp.ClientSession(headers=_header) as session:
            async with session.put(url=f"{self._CHARTS_URL}/{chart_id}/data", data=data.to_csv(index=False, encoding="utf-8")) as resp:
                 pass
            await session.close()


        _header["content-type"] = "application/json"
        async with aiohttp.ClientSession(headers=_header) as session:
            async with session.post(url=f"{self._PUBLISH_URL}/{chart_id}/publish") as resp:
                pass
            await session.close()

        return f"https://datawrapper.dwcdn.net/{chart_id}/full.png"



