import threading
import traceback

import disnake
import sentry_sdk
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from pymongo import MongoClient
from pytz import utc

from classes.bot import CustomClient
from utility.startup import create_config, get_cluster_breakdown, load_cogs, sentry_filter


scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

config = create_config()

intents = disnake.Intents(guilds=True, members=True, emojis=True, messages=True, message_content=True)

db_client = MongoClient(config.static_mongodb)
cluster_kwargs = get_cluster_breakdown(config=config)

bot = CustomClient(
    command_prefix='??',
    help_command=None,
    intents=intents,
    scheduler=scheduler,
    config=config,
    chunk_guilds_at_startup=(not config.is_main),
    **cluster_kwargs,
)

initial_extensions = [
    'discord.events',
    'discord.autocomplete',
    'discord.converters',
    'background.tasks.background_cache',
    'background.features.link_parsers',
    'background.logs.giveaway',
]

# only the local version can not run
if not config.is_beta:
    initial_extensions += [
        'exceptions.handler',
        'background.logs.autorefresh',
        'background.logs.bans',
        'background.logs.capital',
        'background.logs.donations',
        'background.logs.joinleave',
        'background.logs.legends',
        'background.logs.playerupgrades',
        'background.logs.reddit',
        'background.logs.reminders',
        'background.features.voicestat_loop',
        'background.features.auto_refresh',
        'background.logs.war',
        'background.features.refresh_boards',
    ]
health_app = FastAPI()


@health_app.get('/health')
async def health_check():
    if bot.is_ready():
        return {'status': 'ok', 'details': 'Bot is running and ready'}
    else:
        return {'status': 'error', 'details': 'Bot is not ready'}


def run_health_check_server():
    uvicorn.run(health_app, host='127.0.0.1', port=8027)


if __name__ == '__main__':

    # Start FastAPI server in a background thread
    threading.Thread(target=run_health_check_server, daemon=True).start()

    sentry_sdk.init(
        dsn=config.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        before_send=sentry_filter,
    )
    initial_extensions += load_cogs(disallowed=set())
    for count, extension in enumerate(initial_extensions):
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    bot.EXTENSION_LIST.extend(initial_extensions)
    bot.run(config.bot_token)
