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
reddit_ee = EventEmitter()

from aiokafka import AIOKafkaConsumer, TopicPartition


async def kafka_events(bot: disnake.Client):
    topic = "reminder"
    consumer: AIOKafkaConsumer = AIOKafkaConsumer(topic, bootstrap_servers='85.10.200.219:9092')
    await consumer.start()
    await bot.wait_until_ready()
    print("here")

    partitions = consumer.partitions_for_topic(topic)
    topic_partitions = [TopicPartition(topic, p) for p in partitions]  # Create TopicPartitions
    end_offsets = await consumer.end_offsets(topic_partitions)
    for tp, offset in end_offsets.items():
        new_offset = max(0, offset - 10)  # Ensure non-negative offset
        consumer.seek(tp, new_offset)

    found = 0
    for _ in range(10):  # Consume approximately 10 messages
        msg = await consumer.getone()
        json_message = orjson.loads(msg.value)
        if (f := json_message.get("type")) is not None:
            fields = [f]
        else:
            fields = json_message.get("types", [])
        for field in fields:
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

    '''try:
        async for msg in consumer:
            json_message = orjson.loads(msg.value)
            print(json_message)
            if (f := json_message.get("type")) is not None:
              fields = [f]
            else:
              fields = json_message.get("types", [])
            print(fields)
            continue
            for field in fields:
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
                if awaitable is not None:
                    await awaitable
    finally:
        await consumer.stop()'''