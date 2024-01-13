import datetime
import os
import coc
from uvicorn import Config, Server
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from discordwebhook import Discord

import motor.motor_asyncio
import asyncio
import pytz

from clash import setup_coc, clash_client
from events import clan_events
from events import war_events
from events import raid_events
import sockets

utc = pytz.utc
app = FastAPI()

app.add_api_websocket_route("/clans", endpoint=sockets.clan_websocket)
app.add_api_websocket_route("/wars", endpoint=sockets.war_websocket)
app.add_api_websocket_route("/raids", endpoint=sockets.raid_websocket)

@app.on_event("startup")
async def startup_event():
    await setup_coc()


db_client = motor.motor_asyncio.AsyncIOMotorClient(os.environ.get("DB_LOGIN"))
usafam = db_client.usafam
clan_db = usafam.clans

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("LOOPER_LOGIN"))
new_looper = client.new_looper
player_stats = new_looper.player_stats

clan_tags = asyncio.get_event_loop().run_until_complete(clan_db.distinct("tag"))
clash_client.add_clan_updates(*clan_tags)


@coc.ClientEvents.clan_loop_start()
async def start(iter_spot):
    clan_tags = await clan_db.distinct("tag")
    #db_tags = await player_stats.distinct("clan_tag")
    #clan_tags = list(set(clan_tags + db_tags))
    clash_client.add_clan_updates(*clan_tags)
    clash_client.add_war_updates(*clan_tags)
    clash_client.add_raid_updates(*clan_tags)


#add events
clash_client.add_events(start, clan_events.member_join, clan_events.member_leave, clan_events.member_donos, clan_events.any_change)
clash_client.add_events(war_events.new_war, war_events.war_attack)
clash_client.add_events(raid_events.raid_attack, raid_events.state)


loop = asyncio.get_event_loop()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
config = Config(app=app, loop="asyncio",host= "85.10.200.219", port=60123, ws_ping_interval=3600, ws_ping_timeout=3600, timeout_keep_alive=3600, timeout_notify=3600)
server = Server(config)
loop.create_task(server.serve())
loop.run_forever()


