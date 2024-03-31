import asyncio

import disnake
import orjson
from classes.config import Config
from pymitter import EventEmitter

config = Config()
player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()
raid_ee = EventEmitter()
reminder_ee = EventEmitter()

from aiokafka import AIOKafkaConsumer, TopicPartition


async def kafka_events(bot: disnake.Client):
    topic = "player"
    consumer: AIOKafkaConsumer = AIOKafkaConsumer(topic, bootstrap_servers='85.10.200.219:9092')
    await consumer.start()
    await bot.wait_until_ready()
    try:
        async for msg in consumer:
            json_message = orjson.loads(msg.value)

            if (f := json_message.get("type")) is not None:
              fields = [f]
            else:
              fields = json_message.get("types", [])

            if "heroes" not in fields:
                continue

            for field in fields:
                if field != "heroes":
                    continue
                awaitable = None
                if msg.topic == "player":
                    awaitable = player_ee.emit_async(field, json_message)
                elif msg.topic == "war":
                    awaitable = war_ee.emit_async(field, json_message)
                if msg.topic == "clan":
                    awaitable = clan_ee.emit_async(field, json_message)
                elif msg.topic == "capital":
                    awaitable = raid_ee.emit_async(field, json_message)
                if awaitable is not None:
                    await awaitable

        '''async for msg in consumer:
            print(msg)
            continue
            json_message = orjson.loads(msg.value)

            field = json_message["type"]
            awaitable = None
            if msg.topic == "player":
                awaitable = player_ee.emit_async(field, json_message)
            elif msg.topic == "war":
                awaitable = war_ee.emit_async(field, json_message)
            if msg.topic == "clan":
                awaitable = clan_ee.emit_async(field, json_message)
            elif msg.topic == "capital":
                awaitable = raid_ee.emit_async(field, json_message)
            if awaitable is not None:
                await awaitable'''
    finally:
        await consumer.stop()