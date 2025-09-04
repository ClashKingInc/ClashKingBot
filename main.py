import coc
import hikari
import lightbulb

from api.client import ClashKingAPIClient
from classes.cocpy.client import CustomClashClient
from classes.config import Config
from classes.mongo import MongoClient
from commands.ext.hooks import auto_defer_command_response
from discord.startup import create_config, load_cogs
from utility.constants import EMBED_COLOR_CLASS
from utility.emojis import fetch_emoji_dict
from utility.translations import fluent_provider

config = create_config()

# Create a GatewayBot instance
bot = hikari.GatewayBot(
    token=config.bot_token,
    auto_chunk_members=False,
)

client = lightbulb.client_from_app(
    app=bot, localization_provider=fluent_provider(), hooks=[auto_defer_command_response]
)

registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)

registry.register_value(Config, config)
registry.register_factory(
    ClashKingAPIClient,
    lambda: ClashKingAPIClient(api_token=config.clashking_api_token, timeout=30, cache_ttl=180),
)
clash_client = CustomClashClient(
    base_url='https://proxy.clashk.ing/v1',
    key_count=10,
    key_names='test',
    throttle_limit=500,
    cache_max_size=10_000,
    load_game_data=coc.LoadGameData(default=True),
    raw_attribute=True,
    stats_max_size=10_000,
)
registry.register_value(CustomClashClient, clash_client)

mongo_client = MongoClient(uri=config.stats_mongodb, compressors=['snappy', 'zlib'])
registry.register_value(hikari.GatewayBot, bot)

registry.register_value(MongoClient, mongo_client)


async def color() -> hikari.Color:
    return EMBED_COLOR_CLASS


registry.register_factory(hikari.Color, color)


@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    await fetch_emoji_dict(bot=bot, config=config)

    # Load any extensions
    print(load_cogs(disallowed=set()))
    extensions = load_cogs(disallowed=set())
    extensions = ["commands.compo", "commands.war"]
    await client.load_extensions(*extensions)
    # Start the bot - make sure commands are synced properly
    await client.start()
    await clash_client.login_with_tokens('')


bot.run()
