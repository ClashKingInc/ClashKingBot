import asyncio
from typing import TYPE_CHECKING

import orjson
import ujson
import websockets
from loguru import logger
from pymitter import EventEmitter


if TYPE_CHECKING:
    from classes.bot import CustomClient


player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()
raid_ee = EventEmitter()
reminder_ee = EventEmitter()
reddit_ee = EventEmitter()


async def kafka_events(bot: 'CustomClient'):
    async def wrap_task(f: callable):
        await asyncio.sleep(0)
        await f

    background_tasks = set()
    while True:
        clans = set()
        while not bot.CLANS_LOADED:
            await asyncio.sleep(15)
        try:
            async with websockets.connect(
                f'ws://85.10.200.219:8001/events',
                ping_timeout=None,
                ping_interval=None,
                open_timeout=None,
                max_queue=500_000,
            ) as websocket:
                await websocket.send(ujson.dumps({'clans': list(bot.OUR_CLANS)}).encode('utf-8'))

                async for message in websocket:
                    if clans != bot.OUR_CLANS:
                        await websocket.send(ujson.dumps({'clans': list(bot.OUR_CLANS)}).encode('utf-8'))
                        clans = bot.OUR_CLANS

                    if 'Login!' in str(message):
                        logger.info(message)
                    else:
                        try:
                            json_message = orjson.loads(message)
                            topic = json_message.get('topic')

                            value = json_message.get('value')

                            if (f := value.get('type')) is not None:
                                fields = [f]
                            else:
                                fields = value.get('types', [])

                            for field in fields:
                                value['trigger'] = field
                                awaitable = None
                                if topic == 'player':
                                    awaitable = player_ee.emit_async(field, value)
                                elif topic == 'war':
                                    awaitable = war_ee.emit_async(field, value)
                                if topic == 'clan':
                                    awaitable = clan_ee.emit_async(field, value)
                                elif topic == 'capital':
                                    awaitable = raid_ee.emit_async(field, value)
                                elif topic == 'reminder':
                                    awaitable = reminder_ee.emit_async(field, value)
                                elif topic == 'reddit':
                                    awaitable = reddit_ee.emit_async(field, value)
                                if awaitable is not None:
                                    task = asyncio.create_task(wrap_task(awaitable))
                                    background_tasks.add(task)
                                    task.add_done_callback(background_tasks.discard)
                        except Exception:
                            pass
        except Exception as e:
            print(e)
            continue
