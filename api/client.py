import re
from functools import wraps
from typing import Any

import aiohttp
import coc
from expiring_dict import ExpiringDict

from api.bans import BanListItem, BanResponse
from api.clan import BasicClan, ClanCompo, ClanTotals
from api.errors import APIUnavailableError, AuthenticationError, NotFoundError
from api.location import ClanRanking
from api.other import ObjectDictIterable
from api.player import DonationPlayer, LocationPlayer, Player, SortedPlayer, Summary, WarStatsPlayer
from api.route import Route
from api.search import ClanSearchResult, Group
from api.server import ServerClanSettings, ServerSettings
from api.war import CWLRanking, CWLThreshold


def handle_silent(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        silent = kwargs.pop('silent', False)  # Extract 'silent' if provided, default to False
        try:
            return await func(*args, **kwargs)
        except NotFoundError:
            if silent:
                return None
            raise

    return wrapper


# fmt: off
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
        cache_key = f'{route.method}:{route.endpoint}'

        # Check cache for GET requests
        if method == 'get' and cache_key in self.cache:
            return self.cache[cache_key]

        headers = {'Authorization': f'Bearer {self.api_token}', 'Accept-Encoding': 'gzip'}

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.request(
                    method=method,
                    url=url,
                    data=route.data,
                    json=route.json,
                    timeout=self.timeout,
                ) as response:
                    #print(await response.text())
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
    async def add_ban(
            self,
            server_id: int,
            player_tag: str,
            reason: str | None,
            added_by: int,
            image: str | None
    ) -> BanResponse:
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
                json={'reason': reason, 'added_by': added_by, "image": image},
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
    async def get_server_settings(self, server_id: int, with_clan_settings: bool = False) -> ServerSettings:
        server_id = server_id or 0
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/server/{server_id}/settings',
                clan_settings=with_clan_settings,
            )
        )
        return ServerSettings(data=response)


    @handle_silent
    async def get_server_clan_settings(self, server_id: int, clan_tag: str) -> ServerClanSettings | None:
        server_id = server_id or 0
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/server/{server_id}/clan/{clan_tag}/settings',
            )
        )
        return ServerClanSettings(data=response)


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


    async def get_basic_server_clan_list(self, server_id: int) -> list[BasicClan]:
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/link/server/{server_id}/clan/list',
            )
        )
        return [BasicClan(data=data) for data in response['items']]




    #PLAYER ENDPOINTS
    async def get_player_locations(self, player_tags: list[str]) -> ObjectDictIterable[LocationPlayer]:
        """
        Gets location info for a list of players.

        :param player_tags: List of player tags.
        """
        response = await self._request(
            Route(
                method='POST',
                endpoint='/v2/players/location',
                json={"player_tags": player_tags},
            )
        )
        items = response['items']
        return ObjectDictIterable(items=[LocationPlayer(data=item) for item in items], key='tag')


    async def get_sorted_players(self, sort_by: str, player_tags: list[str]) -> ObjectDictIterable[SortedPlayer]:
        """
        Gets players sorted by a specified criteria. Returns a stripped down version of the Player object.
        """
        response = await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/players/sorted/{sort_by}',
                json={"player_tags": player_tags},
            )
        )
        items = response['items']
        return ObjectDictIterable(items=[SortedPlayer(data=item) for item in items], key='tag')


    async def get_players_summary(self, season: str, limit: int, player_tags: list[str]) -> Summary:
        """
        Gets players sorted by a specified criteria. Returns a stripped down version of the Player object.
        """
        response = await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/players/summary/{season}/top',
                limit=limit,
                json={"player_tags": player_tags},
            )
        )
        items = response['items']
        return Summary(items=items)



    # CLAN ENDPOINTS
    async def get_clan_totals(self, clan_tag: str, player_tags: list[str]) -> ClanTotals:
        """
        Retrieves the clan totals for a specified clan.
        """
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/clan/{clan_tag}/board/totals',
                json={'player_tags': player_tags}
            )
        )
        return ClanTotals(data=response)


    @handle_silent
    async def get_clan_ranking(self, clan_tag: str) -> ClanRanking:
        """
        Gets location info for a list of players.

        :param clan_tag: tag for clan
        """
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/clan/{clan_tag}/ranking',
            )
        )
        return ClanRanking(data=response)



    async def get_clan_war_stats(
            self,
            clan_tags: list[str],
            timestamp_start: int = 0,
            timestamp_end: int = 9999999999,
            war_types: int = 7,
            townhall_filter: str = 'all',
            limit: int = 1000,
    ) -> list[WarStatsPlayer]:
        response = await self._request(
            Route(
                method='GET',
                endpoint='/v2/war/clan/stats',
                clan_tags=clan_tags,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                townhall_filter=townhall_filter,
                war_types=war_types,
                limit=limit,
            )
        )
        items = response['items']
        return [WarStatsPlayer(data=item) for item in items]


    async def get_clan_compo(
            self,
            clan_tags: list[str],
    ) -> ClanCompo:
        response = await self._request(
            Route(
                method='GET',
                endpoint='/v2/clan/compo',
                clan_tags=clan_tags
            )
        )
        return ClanCompo(data=response)



    #WAR ENDPOINTS
    async def get_previous_clan_wars(
            self,
            clan_tag: str,
            timestamp_start = None,
            timestamp_end = None,
            include_cwl = False,
            limit = 50,
    ) -> list[coc.ClanWar]:
        """
        :param clan_tag: tag for clan
        """
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/war/{clan_tag}/previous',
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                include_cwl=include_cwl,
                limit=limit,
            )
        )
        items = response['items']
        return [coc.ClanWar(data=data, clan_tag=clan_tag, client=None) for data in items]


    async def get_cwl_ranking_history(
            self,
            clan_tag: str
    ) -> list[CWLRanking]:
        """
        :param clan_tag: tag for clan
        """
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/cwl/{clan_tag}/ranking-history',
            )
        )
        items = response['items']
        return [CWLRanking(data=data) for data in items]

    async def get_cwl_league_thresholds(
            self,
    ) -> list[CWLThreshold]:
        response = await self._request(
            Route(
                method='GET',
                endpoint='/v2/cwl/league-thresholds',
            )
        )
        items = response['items']
        return [CWLThreshold(data=data) for data in items]



    # SEARCH ENDPOINTS
    async def search_for_clans(
            self,
            query: str,
            user_id: int = 0,
            guild_id: int = 0,
    ) -> list[ClanSearchResult]:

        response = await self._request(
            Route(
                method='GET',
                endpoint='/v2/search/clan',
                query=query,
                user_id=user_id or 0,
                guild_id=guild_id or 0,
            )
        )
        items = response['items']
        return [ClanSearchResult(data=data) for data in items]

    async def search_for_bans(
            self,
            query: str,
            guild_id: int = 0,
    ) -> list[Player]:
        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/search/{guild_id}/banned-players',
                query=query,
            )
        )
        items = response['items']
        return [Player(data=data) for data in items]


    async def add_recent_search(
            self,
            tag: str,
            type: int,
            user_id: int,
    ) -> bool:

        await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/search/recent/{user_id}/{type}/{tag}',
            )
        )
        return True

    async def create_group(
            self,
            user_id: int,
            name: str,
            type: int,
    ) -> bool:

        await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/search/groups/{user_id}/{name}/{type}',
            )
        )
        return True

    async def group_add(
            self,
            group_id: int,
            tag: str
    ) -> bool:

        await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/search/groups/{group_id}/add/{tag}',
            )
        )
        return True

    async def group_remove(
            self,
            group_id: int,
            tag: str
    ) -> bool:

        await self._request(
            Route(
                method='POST',
                endpoint=f'/v2/search/groups/{group_id}/remove/{tag}',
            )
        )
        return True

    async def get_group(
            self,
            group_id: str,
    ) -> Group:

        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/search/groups/{group_id}',
            )
        )
        return Group(data=response)

    async def delete_group(
            self,
            group_id: int,
    ) -> bool:

        await self._request(
            Route(
                method='DELETE',
                endpoint=f'/v2/search/groups/{group_id}',
            )
        )
        return True

    async def get_group_list(
            self,
            user_id: int,
    ) -> list[Group]:

        response = await self._request(
            Route(
                method='GET',
                endpoint=f'/v2/search/groups/{user_id}/list',
            )
        )
        items = response.get('items', [])
        return [Group(data=d) for d in items]













'''import asyncio


async def foo():
    client = ClashKingAPIClient(api_token='XRKHJDBmTBILFepA7I5rKxwwBWQu', timeout=30, cache_ttl=60)
    player_tags = ["#2J8V28GV0", "#PVLRQQUJ", "#Q9YLRPUV", "#2LGQJ2GU8", "#C02UPP2P",
 "#YL0CCGV2G", "#JPQC2Y02", "#C9V8PC90", "#2QJYRU88", "#LP9Y9Q8PG",
 "#2GGUJVUGY", "#8GLYGGJQ", "#L20LQLULY", "#QCG229VY", "#QPGU0YR2L",
 "#2PYGPPJ", "#PQYJGL2PL", "#YGYPR9YR", "#8RRQVYU", "#829CC0CY",
 "#LGR29G2YV", "#PVCR00Y8L", "#80Y0C0VU", "#YU22G22Y", "#YQ2P00CQ",
 "#90J9828JG", "#PR0J29P", "#282L8YR0Q", "#2YLPC28V", "#C0U0JJQR",
 "#8V9QGJGU", "#YYVV2QPP", "#YUVPLUU8P", "#YV9JCQYU0", "#UJQVGJPG",
 "#QJGYLJVL0", "#GPRJV8LGV", "#GQYRGYVJ8"]
    """response = await client.get_clan_war_stats(clan_tag="#2PP",
                                               timestamp_start=0,
                                               timestamp_end=9999999999
                                               )
"""

asyncio.run(foo())'''
