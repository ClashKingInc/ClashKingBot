import traceback

import disnake
import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
]

# only the local version can not run
if not config.is_beta:
    initial_extensions += [
        "exceptions.handler",
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
        "background.features.auto_refresh",
        'background.logs.war',
        "background.features.refresh_boards"
    ]


if __name__ == '__main__':
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
