import asyncio
from typing import TYPE_CHECKING, Dict, Tuple, Type

import orjson
import ujson
import websockets
from websockets.asyncio.client import connect
from loguru import logger
from .register import registered_logs
from collections import deque, defaultdict

if TYPE_CHECKING:
    from classes.bot import CustomClient

from .event import BaseEvent, ClanEvent, PlayerEvent


class EventGateway:
    def __init__(self):
        self.background_tasks = set()
        self.clans = set()
        self.bot: 'CustomClient' = None
        self.defaults = {'ping_timeout': None, 'ping_interval': None, 'open_timeout': None, 'max_queue': 500_000}
        self.websocket: websockets.asyncio.client.Connection = None
        self.request_stats = defaultdict(lambda: deque(maxlen=10_000))
        self.available_topics = set(list(self.emitter_map.keys()))

    @property
    def available_events(self) -> set:
        return {
            'player',
            'war',
            'clan',
            'capital',
            'reminder',
            'reddit',
            'giveaway',
        }

    async def _before_start(self):
        while not self.bot.OUR_CLANS or self.bot._config.is_beta:
            await asyncio.sleep(1)

    async def wrap_task(self, f: callable):
        await asyncio.sleep(0)
        await f

    async def _update_clan_list(self):
        if self.clans != self.bot.OUR_CLANS:
            await self.websocket.send(
                ujson.dumps(
                    {
                        'client_id': f'{self.bot.application_id}-{self.bot._config.cluster_id}',
                        'clans': list(self.bot.OUR_CLANS),
                    }
                ).encode('utf-8')
            )
            self.clans = self.bot.OUR_CLANS

    async def _message_handler(self, message: bytes):
        """
        take in an event from the websocket and handle it
        parse event type and send to the registered log function for that event
        """
        if 'Login!' in str(message):
            return logger.info(message)

        try:
            json_message = orjson.loads(message)
            """
            topic is a base event type like player, giveaway, reddit, clan, etc
            type(s) is what kind of event this is (and in some events maps to direct field changes in value)
            value is the data for the event such as old_clan, player_clan
            """
            topic = json_message.get('topic')
            if topic not in self.available_topics:
                return
            value = json_message.get('value')

            fields = value.get('types', [value.get('type')])
            for field in fields:

                event_type = f'{topic}:{field}'
                value['event_type'] = event_type

                """
                this is how event types for triggers are defined
                such as player:troops
                add it to the value data, as some functions need it internally
                """
                if event_type not in self.available_events:
                    return

                log_function, event_cls = registered_logs[event_type]
                if event_cls:
                    value = event_cls(data=value)
                """
                all log functions have the 2 params of bot & event
                event always must be a class w/ data param, 
                but leaving open possibility it could be set to None
                """
                task = asyncio.create_task(self.wrap_task(log_function(bot=self.bot, event=value)))
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
        except Exception:
            """
            silently ignore errors for now
            mainly in case a malformed event is sent
            """
            pass

    async def run(self):
        await self._before_start()
        async for websocket in connect(f'{self.bot._config.clash_event_ws}', **self.defaults):
            try:
                self.websocket = websocket
                await self._update_clan_list()
                async for message in websocket:
                    await self._update_clan_list()
                    await self._message_handler(message=message)
            except websockets.exceptions.WebSocketException:
                continue
