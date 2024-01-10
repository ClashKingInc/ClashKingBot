import os
import disnake
import traceback
import motor.motor_asyncio
import sentry_sdk
from CustomClasses.CustomBot import CustomClient
from disnake import Client
from disnake.ext import commands
import argparse

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from Background.Logs.event_websockets import kafka_events

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

parser = argparse.ArgumentParser(description="Just an example", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-c", "--custom", action="store_true", help="custom mode")
parser.add_argument("-b", "--beta", action="store_true", help="beta mode")
parser.add_argument("-k", "--test", action="store_true", help="test mode")
parser.add_argument("-t", "--token", help="token")

args = parser.parse_args()
config = vars(args)

IS_BETA = config.get("beta", False)
IS_CUSTOM = config.get("custom", False)
IS_TEST = config.get("test", False)
TOKEN = config.get("token")

discClient = Client()
intents = disnake.Intents().none()
intents.guilds = True
intents.members = True
intents.emojis = True
intents.messages = True
intents.message_content = True

bot = CustomClient(command_prefix="??",help_command=None, intents=intents)

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
    #"BoardCommands.Commands.ClanCommands",
    #"BoardCommands.Commands.TopCommands",
    #"BoardCommands.Commands.FamilyCommands",
    #"BoardCommands.Commands.PlayerCommands",
    #"BoardCommands.Buttons.Buttons",
    #"BoardCommands.Commands.WarCommands",
    #"BoardCommands.Buttons.Clan",
    #"Exceptions.ExceptionHandler",
    "Export.ExportsCog",
    "FamilyManagement.Reminders.Reminders",
    "FamilyManagement.strikes",
    "FamilyManagement.rosters",
    "Legends & Trophies.leaderboards",
    "Settings.settings",
    "Settings.setup",
    "Settings.autoboard",
    "Settings.addclans",
    #"Utility.awards",
    #"Utility.boost",
    #"Utility.bases",
    #"Utility.link_parsers",
    #"Utility.help",
    #"Utility.other",
    #"Link_and_Eval.link_button",
    "Discord.events",
    "Discord.autocomplete",
    "Discord.converters",
    #"Background.refresh_boards",
    "Graphing.Graphs",

]

disallowed = set()
if IS_CUSTOM:
    disallowed.add("Owner")

def load():
    for root, _, files in os.walk('./Commands'):
        for filename in files:
            if filename.endswith('.py') and filename.split(".")[0] in ["commands", "click"]:
                path = os.path.join(root, filename)[len("./Commands/"):][:-3].replace(os.path.sep, '.')
                if path.split(".")[0] in disallowed:
                    continue
                bot.load_extension(f'Commands.{path}')
                bot.EXTENSION_LIST.append(f'Commands.{path}')



#dont let custom or local run
if not IS_BETA and not IS_CUSTOM:
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
if not IS_TEST:
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
        dsn=os.getenv("DSN"),
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
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()

    if not IS_BETA:
        bot.loop.create_task(kafka_events())

    bot.run(TOKEN)
