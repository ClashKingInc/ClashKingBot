import aiohttp
import re
from typing import Any
from expiring_dict import ExpiringDict

from route import Route

from api.bans import BanListItem, BanResponse
from api.errors import APIUnavailableError, AuthenticationError, NotFoundError
from api.other import ObjectDictIterable
from api.player import LocationPlayer
from api.server import ServerSettings


class ClashKingAPIClient:
    def __init__(self, api_token: str, timeout: int = 30, cache_ttl: int = 60):
        # self.base_url = 'https://api.clashk.ing'
        self.base_url = 'http://localhost:8000'
        self.api_token: str = api_token
        self.timeout: int = timeout
        self.cache = ExpiringDict()
        self.default_cache_ttl: int = cache_ttl

    def _parse_cache_control(self, cache_control: str) -> int:
        max_age_match = re.search(r'max-age=(\d+)', cache_control)
        if max_age_match:
            return int(max_age_match.group(1))
        return self.default_cache_ttl

    async def _request(self, route: Route) -> dict[str, Any]:
        """Handles all HTTP requests, caching GET requests and raising appropriate exceptions."""
        url = f'{self.base_url}{route.endpoint}'
        method = route.method.lower()
        cache_key = f'{route.method}:{route.endpoint}:{route.params}'

        # Check cache for GET requests
        if method == 'get' and cache_key in self.cache:
            return self.cache[cache_key]

        headers = {'Authorization': f'Bearer {self.api_token}', 'Accept-Encoding': 'gzip'}

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=route.params if method in {'get', 'post'} else None,
                    data=route.data if method in {'post', 'put'} else None,
                    json=route.json if method == 'post' else None,
                    timeout=self.timeout,
                ) as response:
                    if response.status == 403:
                        raise AuthenticationError('Invalid authentication token or missing authorization.')

                    if response.status == 404:
                        error_data = await response.json()
                        raise NotFoundError(error_data.get('detail', 'Resource not found.'))

                    if response.status in {500, 502, 503, 504}:  # API is down
                        raise APIUnavailableError(response.status)

                    response.raise_for_status()

                    data = await response.json()

                    if method == 'get':
                        cache_control = response.headers.get('Cache-Control', '')
                        ttl = self._parse_cache_control(cache_control)
                        self.cache[cache_key] = data
                        self.cache.ttl(key=cache_key, value=data, ttl=ttl)

                    return data

            except aiohttp.ClientError as e:
                raise APIUnavailableError(500) from e  # Handle connection issues as API being down

    # BANS
    async def add_ban(self, server_id: int, player_tag: str, reason: str, added_by: int) -> BanResponse:
        """
        Adds a ban for a player on a specific server.

        :param server_id: The ID of the server where the ban is applied.
        :param player_tag: The unique tag identifying the player.
        :param reason: The reason for banning the player.
        :param added_by: The ID of the user initiating the ban.
        :return: A BanResponse object containing the result of the operation.
        """
        response = await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/ban/add/{server_id}/{player_tag}',
                data={'reason': reason, 'added_by': added_by, 'rollover_days': None},
            )
        )
        return BanResponse(data=response)

    async def remove_ban(self, server_id: int, player_tag: str) -> BanResponse:
        """
        Removes a ban for a given player in a specific server.

        :param server_id: The ID of the server where the ban should be removed.
        :param player_tag: The player's unique tag whose ban is to be removed.
        :return: A BanResponse object containing the result of the operation.
        """
        response = await self._request(
            Route(
                method='DELETE',
                endpoint=f'/v2/ban/remove/{server_id}/{player_tag}',
            )
        )
        return BanResponse(data=response)

    async def get_ban_list(self, server_id: int) -> ObjectDictIterable[BanListItem]:
        """
        Retrieves a list of banned items for a specified server.

        :param server_id: The ID of the server to retrieve the ban list for.
        :return: A list of BanListItem objects representing the banned items.
        """
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/ban/list/{server_id}',
            )
        )
        items = response['items']
        return ObjectDictIterable(items=[BanListItem(data=item) for item in items], key='tag')

    # SETTINGS
    async def get_server_settings(self, server_id: int, with_clan_settings: bool = False):
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/server/settings/{server_id}?clan_settings={with_clan_settings}',
            )
        )
        return ServerSettings(data=response['settings'])


    async def set_server_embed_color(self, server_id: int, embed_color: str):
        """
        Sets the embed color for a specified server.

        :param server_id: The ID of the server to update the embed color for.
        :param embed_color: The hex code of the color to set (e.g., '#FFFFFF').
        :return: The response from the server after updating the embed color.
        """
        hex_code = embed_color.replace('#', '')
        hex_code = int(hex_code, 16)

        response = await self._request(
            Route(
                method='PUT',
                endpoint=f'/v2/server/{server_id}/embed-color/{hex_code}',
            )
        )
        return response

    #PLAYER ENDPOINTS
    async def get_player_locations(self, player_tags: list[str]) -> ObjectDictIterable[LocationPlayer]:
        """
        Gets location info for a list of players.

        :param player_tags: List of player tags.
        """
        response = await self._request(
            Route(
                method='POST',
                endpoint='v2/players/location',
                json={"player_tags": player_tags},
            )
        )
        items = response['items']
        return ObjectDictIterable(items=[LocationPlayer(data=item) for item in items], key='tag')



import asyncio


async def foo():
    client = ClashKingAPIClient(api_token='XRKHJDBmTBILFepA7I5rKxwwBWQu', timeout=30, cache_ttl=60)
    list = await client.get_ban_list(server_id=923764211845312533)


asyncio.run(foo())
