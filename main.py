import os
import disnake
import traceback
import motor.motor_asyncio
import sentry_sdk
from classes.bot import CustomClient
from disnake.ext import commands
from classes.config import Config

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from background.logs.event_websockets import kafka_events

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

bot = CustomClient(command_prefix="??", help_command=None, intents=intents, scheduler=scheduler, config=config)

def check_commands():
    async def predicate(ctx: disnake.ApplicationCommandInteraction):
        if ctx.author.id == 706149153431879760:
            return True
        roles = (await ctx.guild.getch_member(member_id=ctx.author.id)).roles
        if disnake.utils.get(roles, name="ClashKing Perms") != None:
            return True
        db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
        whitelist = db_client.usafam.whitelist
        member = ctx.author

        commandd = ctx.application_command.qualified_name
        if commandd == "unlink":
            return True
        guild = ctx.guild.id

        results =  whitelist.find({"$and" : [
                {"command": commandd},
                {"server" : guild}
            ]})

        if results is None:
            return False

        limit = await whitelist.count_documents(filter={"$and" : [
                {"command": commandd},
                {"server" : guild}
            ]})

        perms = False
        for role in await results.to_list(length=limit):
            role_ = role.get("role_user")
            is_role = role.get("is_role")
            if is_role:
                role_ = ctx.guild.get_role(role_)
                if member in role_.members:
                    return True
            else:
                if member.id == role_:
                    return True

        return perms

    return commands.check(predicate)

initial_extensions = [
    "discord.events",
    "discord.autocomplete",
    "discord.converters",
    "background.features.refresh_boards"
]

disallowed = set()

if config.is_custom:
    disallowed.add("owner")

def load():
    for root, _, files in os.walk('commands'):
        for filename in files:
            if filename.endswith('.py') and filename.split(".")[0] in ["commands", "buttons"]:
                path = os.path.join(root, filename)[len("commands/"):][:-3].replace(os.path.sep, '.')
                if path.split(".")[0] in disallowed:
                    continue
                bot.load_extension(f'commands.{path}')
                bot.EXTENSION_LIST.append(f'commands.{path}')



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
    load()
    print(initial_extensions)
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()

    if not config.is_beta:
        bot.loop.create_task(kafka_events())

    bot.run(config.bot_token)
