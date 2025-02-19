import threading
import traceback

import asyncio
import disnake
import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler
#from background.tasks.health import run_health_check_server
from classes.bot import CustomClient
from discord.startup import create_config, get_cluster_breakdown, load_cogs, sentry_filter
from loguru import logger
from pytz import utc

import coc
from classes.cocpy.client import CustomClashClient
asyncio.set_event_loop(asyncio.new_event_loop())

coc_client: CustomClashClient = CustomClashClient(
    base_url='https://proxy.clashk.ing/v1',
    key_count=10,
    key_names='test',
    throttle_limit=500,
    cache_max_size=10_000,
    load_game_data=coc.LoadGameData(default=True),
    raw_attribute=True,
    stats_max_size=10_000,
)

logger.remove()

logger.add(lambda msg: print(msg, end=''), level='INFO')  # Log to stdout

scheduler = AsyncIOScheduler(timezone=utc)



config = create_config()

intents = disnake.Intents(guilds=True, members=True, emojis=True, messages=True, message_content=True)

bot = CustomClient(
    command_prefix='??',
    help_command=None,
    intents=intents,
    scheduler=scheduler,
    config=config,
    chunk_guilds_at_startup=(not config.is_main),
    coc_client=coc_client,
    **get_cluster_breakdown(config=config),
)

initial_extensions = [
    'discord.events',
    'discord.autocomplete',
    'discord.converters',
    "commands.clan.commands",
    "commands.bans.commands",
]


if __name__ == '__main__':
    bot.loop.run_until_complete(coc_client.login_with_tokens(''))

    sentry_sdk.init(
        dsn=config.sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        before_send=sentry_filter,
    )
    #initial_extensions += load_cogs(disallowed=set())
    for count, extension in enumerate(initial_extensions):
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    bot.EXTENSION_LIST.extend(initial_extensions)

    #threading.Thread(target=run_health_check_server, args=[bot], daemon=True).start()
    #bot.loop.create_task(bot.event_gateway.run())
    bot.run(config.bot_token)
