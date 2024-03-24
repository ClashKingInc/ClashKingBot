import os
import disnake
import traceback
import sentry_sdk

from classes.bot import CustomClient

from classes.config import Config

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from background.logs.events import kafka_events

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

config = Config()
intents = disnake.Intents(
    guilds=True,
    members=True,
    emojis=True,
    messages=True,
    message_content=True
)

cluster_id = 0
total_shards = 1
cluster_kwargs = {"shard_count" : None}
if config.is_main:
    total_shards = 6
    cluster_id = int(config.cluster_id)
    offset = cluster_id - 1  # As we start at 1
    number_of_shards_per_cluster = 2
    # Calculate the shard id's this cluster should handle
    # For example on cluster 1 this would be equal to
    # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    shard_ids = [
        i
        for i in range(
            offset * number_of_shards_per_cluster,
            (offset * number_of_shards_per_cluster) + number_of_shards_per_cluster,
        )
        if i < total_shards
    ]
    cluster_kwargs = {
        "shard_ids": shard_ids,
        "shard_count": total_shards,
    }

bot = CustomClient(command_prefix="??", help_command=None, intents=intents, scheduler=scheduler, config=config, chunk_guilds_at_startup=(not config.is_main), **cluster_kwargs)


initial_extensions = [
    "discord.events",
    "discord.autocomplete",
    "discord.converters",
    #"background.features.refresh_boards",
    "exceptions.handler",
    "background.tasks.emoji_refresh"
]



disallowed = set()

if config.is_custom:
    disallowed.add("owner")
    pass

def load():
    file_list = []
    for root, _, files in os.walk('commands'):
        for filename in files:
            if filename.endswith('.py') and filename.split(".")[0] in ["commands", "buttons"]:
                path = os.path.join(root, filename)[len("commands/"):][:-3].replace(os.path.sep, '.')
                if path.split(".")[0] in disallowed:
                    continue
                file_list.append(f'commands.{path}')
    return file_list


#dont let custom or local run
if not config.is_beta and not config.is_custom:
    initial_extensions += [
        "Background.reddit_recruit_feed",
        "Background.region_lb_update"
    ]
    initial_extensions += [
        "Background.legends_history",
        "Other.erikuh_comp",
        "Background.clan_capital",
    ]

#only the local version can not run
if not config.is_beta:
    initial_extensions += [
        "Background.voicestat_loop",
        "Background.Logs.auto_eval",
        "Background.autoboard_loop",
        "Background.Logs.ban_events",
        "Background.Logs.clan_capital_events",
        "Background.Logs.donations",
        "Background.Logs.join_leave_events",
        "Background.Logs.legend_events",
        "Background.Logs.player_upgrade_events",
        "Background.Logs.war_track",
        "Background.background_cache",
    ]


def before_send(event, hint):
    try:
        if "unclosed client session" in str(event["logentry"]["message"]).lower() or "unclosed connector" in str(event["logentry"]["message"]).lower():
            return None
    except:
        pass
    return event

if __name__ == "__main__":
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        _experiments={
            "profiles_sample_rate": 1.0,
        },
        before_send=before_send
    )
    initial_extensions += load()
    for count, extension in enumerate(initial_extensions):
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    bot.EXTENSION_LIST.extend(initial_extensions)
    if not config.is_beta:
        bot.loop.create_task(kafka_events())

    bot.run(config.bot_token)
