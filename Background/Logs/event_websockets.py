import websockets
import orjson
import os

from dotenv import load_dotenv
from pymitter import EventEmitter
from pymongo import InsertOne
from datetime import datetime
load_dotenv()

player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()
raid_ee = EventEmitter()

WEBSOCKET_IP = os.getenv("WEBSOCKET_IP")
NEW_WEBSOCKET_IP = os.getenv("NEW_WEBSOCKET_IP")
WEBSOCKET_USER = os.getenv("WEBSOCKET_USER")
WEBSOCKET_PW = os.getenv("WEBSOCKET_PW")
import os
import pytz
import motor.motor_asyncio
looper_db = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_DB_LOGIN"))
new_looper = looper_db.get_database("new_looper")
bot_stats= looper_db.clashking.bot_stats
import asyncio
from aiokafka import AIOKafkaConsumer


async def kafka_events():
    consumer: AIOKafkaConsumer = AIOKafkaConsumer("clan", "capital", bootstrap_servers='85.10.200.219:9092')
    await consumer.start()
    try:
        async for msg in consumer:
            print(msg)
            json_message = orjson.loads(msg.value)
            field = json_message["type"]
            awaitable = None
            '''if msg.topic == "player":
                awaitable = player_ee.emit_async(field, json_message)
            elif msg.topic == "war":
                awaitable = war_ee.emit_async(field, json_message)'''
            if msg.topic == "clan":
                awaitable = clan_ee.emit_async(field, json_message)
            '''elif msg.topic == "capital":
                awaitable = raid_ee.emit_async(field, json_message)'''
            if awaitable is not None:
                await awaitable
    finally:
        await consumer.stop()