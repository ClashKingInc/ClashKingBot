import disnake
import orjson

from classes.config import Config
from pymitter import EventEmitter
from loguru import logger

config = Config()
player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()
raid_ee = EventEmitter()
reminder_ee = EventEmitter()
reddit_ee = EventEmitter()

from aiokafka import AIOKafkaConsumer, TopicPartition


async def kafka_events(bot: disnake.Client):
    topics = ["clan", "player"]
    consumer: AIOKafkaConsumer = AIOKafkaConsumer(*topics, bootstrap_servers='85.10.200.219:9092')
    await consumer.start()
    await bot.wait_until_ready()
    logger.info("Events Started")
    try:
        async for msg in consumer:
            json_message = orjson.loads(msg.value)
            if (f := json_message.get("type")) is not None:
                fields = [f]
            else:
                fields = json_message.get("types", [])

            for field in fields:
                json_message["trigger"] = field
                awaitable = None
                if msg.topic == "player":
                    awaitable = player_ee.emit_async(field, json_message)
                elif msg.topic == "war":
                    awaitable = war_ee.emit_async(field, json_message)
                if msg.topic == "clan":
                    awaitable = clan_ee.emit_async(field, json_message)
                elif msg.topic == "capital":
                    awaitable = raid_ee.emit_async(field, json_message)
                elif msg.topic == "reminder":
                    awaitable = reminder_ee.emit_async(field, json_message)
                elif msg.topic == "reddit":
                    awaitable = reddit_ee.emit_async(field, json_message)
                if awaitable is not None:
                    await awaitable
    finally:
        await consumer.stop()