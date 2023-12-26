import aiohttp
from typing import List, TYPE_CHECKING
from urllib.parse import urlencode

import disnake
from expiring_dict import ExpiringDict
from datetime import datetime
from coc.errors import NotFound, GatewayError, HTTPException, Forbidden, Maintenance
import re
import asyncio
from .Classes.bans import BannedUser, BannedResponse
from .Classes.settings import DatabaseServer

if TYPE_CHECKING:
    from CustomClasses.CustomBot import CustomClient
else:
    CustomClient = disnake.Client

class HTTPClient():
    def __init__(self):
        self.cache = ExpiringDict()

    async def request(self, route, **kwargs):
        method = route.method
        url = route.url
        if "json" in kwargs:
            kwargs["headers"]["Content-Type"] = "application/json"

        cache_control_key = route.url

        try:
            data = self.cache[cache_control_key]
            return data
        except KeyError:
            pass

        async with aiohttp.ClientSession() as session:
            for tries in range(5):
                try:
                    async with session.request(method, url, **kwargs) as response:
                        data = await response.json()
                        if response.status in (502, 504):
                            # gateway error, retry again
                            await asyncio.sleep(tries * 2 + 1)
                            continue
                        elif response.status == 403:
                            raise Forbidden(403, data)

                        elif response.status == 404:
                            raise NotFound(404, data)

                        elif response.status == 503:
                            raise Maintenance(503, data)

                        delta = int(response.headers["Cache-Control"].strip("max-age=").strip("public max-age="))
                        self.cache.ttl(key=cache_control_key, value=data, ttl=delta)

                        await session.close()
                        return data
                except asyncio.TimeoutError:
                    # api timed out, retry again
                    if tries > 3:
                        raise GatewayError("The API timed out waiting for the request.")
                    await asyncio.sleep(tries * 2 + 1)
                    continue
            else:
                await session.close()
                if response.status in (502, 504):
                    if isinstance(data, str):
                        # gateway errors return HTML
                        text = re.compile(r"<[^>]+>").sub(data, "")
                        raise GatewayError(response, text)

                    raise GatewayError(response, data)
                raise HTTPException(response, data)


class Route:
    """Helper class to create endpoint URLs."""

    BASE = "https://api.clashking.xyz"

    def __init__(self, method: str, path: str, **kwargs: dict):
        """
        The class is used to create the final URL used to fetch the data
        from the API. The parameters that are passed to the API are all in
        the GET request packet. This class will parse the `kwargs` dictionary
        and concatenate any parameters passed in.

        Parameters
        ----------
        method:
            :class:`str`: HTTP method used for the HTTP request
        path:
            :class:`str`: URL path used for the HTTP request
        kwargs:
            :class:`dict`: Optional options used to concatenate into the final
            URL
        """
        if "#" in path:
            path = path.replace("#", "%23")

        self.method = method
        self.path = path
        url = self.BASE + self.path

        if kwargs:
            self.url = "{}?{}".format(url, urlencode({k: v for k, v in kwargs.items() if v is not None}, True))
        else:
            self.url = url


class ClashKingAPIClient():
    def __init__(self, api_token: str, bot: CustomClient):
        self.bot = bot
        self.__http_client = HTTPClient()
        self.api_token = api_token
        self.api_token_query = {"api_token" : self.api_token}


    async def get_ban_list(self, server_id: int, **kwargs):
        kwargs = kwargs | self.api_token_query
        data = await self.__http_client.request(Route("GET", f"/ban/{server_id}/list", **kwargs))
        return [BannedUser(data=d, client=self) for d in data.get("items")]


    async def add_ban(self, server_id: int, player_tag: str,  **kwargs):
        if kwargs.get("rollover_days") is None:
            del kwargs["rollover_days"]
        kwargs = kwargs | self.api_token_query
        data = await self.__http_client.request(Route("POST", f"/ban/{server_id}/add/{player_tag}", **kwargs))
        return BannedResponse(data=data, client=self)


    async def get_server_settings(self, server_id: int, **kwargs):
        kwargs = kwargs | self.api_token_query
        data = await self.__http_client.request(Route("GET", f"/server-settings/{server_id}", **kwargs))
        return DatabaseServer(bot=self.bot, data=data)



    '''async def get_donations(self, players: List[str] = [], clans: List[str] = [], townhalls: List[int] = [], server: int = None, sort_field: str = "donations",
                            limit: int =50, tied_only: bool= True, season: str= None, descending: bool = True, as_dict: dict=None):
        if not as_dict:
            our_values = locals()
            del our_values["self"]
            delete = [key for key, value in our_values.items() if value is None or value == []]
            for key in delete:
                del our_values[key]
        else:
            our_values = as_dict
        data = await self.__http_client.request(Route("GET", "/donations", **our_values))
        return DonationResponse(data)

    async def get_activity(self, players: List[str] = [], clans: List[str] = [], townhalls: List[int] = [], server: int = None, sort_field: str = "activity",
                            limit: int =50, tied_only: bool= True, season: str= None, descending: bool = True, as_dict: dict=None):
        if not as_dict:
            our_values = locals()
            del our_values["self"]
            delete = [key for key, value in our_values.items() if value is None or value == []]
            for key in delete:
                del our_values[key]
        else:
            our_values = as_dict
        data = await self.__http_client.request(Route("GET", "/activity", **our_values))
        return ActivityResponse(data)

    async def get_clan_games(self, players: List[str] = [], clans: List[str] = [], townhalls: List[int] = [], server: int = None, sort_field: str = "points",
                            limit: int =50, tied_only: bool= True, season: str= None, descending: bool = True, as_dict: dict=None):
        if not as_dict:
            our_values = locals()
            del our_values["self"]
            delete = [key for key, value in our_values.items() if value is None or value == []]
            for key in delete:
                del our_values[key]
        else:
            our_values = as_dict
        data = await self.__http_client.request(Route("GET", "/clan-games", **our_values))
        return ClanGamesResponse(data)'''
