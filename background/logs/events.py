import asyncio
from typing import TYPE_CHECKING, Awaitable

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
giveaway_ee = EventEmitter()


async def kafka_events(bot: 'CustomClient'):
    MAX_BACKGROUND_TASKS = 250
    TASK_TIMEOUT_SECONDS = 10
    WEBSOCKET_MAX_QUEUE = 5_000

    async def wrap_task(awaitable: Awaitable):
        await asyncio.sleep(0)
        await asyncio.wait_for(awaitable, timeout=TASK_TIMEOUT_SECONDS)

    def discard_task(task: asyncio.Task):
        background_tasks.discard(task)
        if task.cancelled():
            return
        try:
            task.result()
        except asyncio.TimeoutError:
            logger.warning(f"Background event task exceeded {TASK_TIMEOUT_SECONDS}s and was cancelled")
        except Exception:
            logger.exception("Background event task failed")

    if bot._config.is_beta:
        return

    background_tasks = set()
    last_task_count_log = 0
    while True:
        clans = set()
        while not bot.OUR_CLANS:
            await asyncio.sleep(1)
        try:
            async with websockets.connect(
                bot._config.websocket_url,
                ping_timeout=None,
                ping_interval=None,
                open_timeout=None,
                max_queue=WEBSOCKET_MAX_QUEUE,
            ) as websocket:
                await websocket.send(
                    ujson.dumps({'client_id': f'{bot.user.id}-{bot._config.cluster_id}', 'clans': list(bot.OUR_CLANS)}).encode('utf-8')
                )
                async for message in websocket:
                    # Log task count every 100 tasks to monitor performance
                    current_task_count = len(background_tasks)
                    if current_task_count > 0 and current_task_count % 100 == 0 and current_task_count != last_task_count_log:
                        logger.info(f"Background tasks running: {current_task_count}/{MAX_BACKGROUND_TASKS}")
                        last_task_count_log = current_task_count
                    if clans != bot.OUR_CLANS:
                        await websocket.send(
                            ujson.dumps({'client_id': f'{bot.application_id}-{bot._config.cluster_id}', 'clans': list(bot.OUR_CLANS)}).encode('utf-8')
                        )
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
                                elif topic == 'giveaway':
                                    awaitable = giveaway_ee.emit_async(field, value)
                                if awaitable is not None:
                                    if len(background_tasks) < MAX_BACKGROUND_TASKS:
                                        task = asyncio.create_task(wrap_task(awaitable))
                                        background_tasks.add(task)
                                        task.add_done_callback(discard_task)
                                    else:
                                        logger.warning(f"Task queue full! {len(background_tasks)} tasks running. Dropping {topic}:{field} event")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Websocket error: {e}")
            # Clean up tasks before reconnecting to prevent accumulation
            for task in background_tasks.copy():
                if task.done():
                    background_tasks.discard(task)
            await asyncio.sleep(5)  # Wait before reconnecting
            continue
