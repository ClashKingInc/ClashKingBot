import orjson
from classes.config import Config
from pymitter import EventEmitter

config = Config()
player_ee = EventEmitter()
clan_ee = EventEmitter()
war_ee = EventEmitter()
raid_ee = EventEmitter()



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