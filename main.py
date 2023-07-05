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
from Background.Logs.event_websockets import player_websocket, clan_websocket, war_websocket

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

parser = argparse.ArgumentParser(description="Just an example",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-c", "--custom", action="store_true", help="custom mode")
parser.add_argument("-b", "--beta", action="store_true", help="beta mode")
parser.add_argument("-t", "--token", help="token")
args = parser.parse_args()
config = vars(args)

IS_BETA = config.get("beta", False)
IS_CUSTOM = config.get("custom", False)
TOKEN = config.get("token")

discClient = Client()
intents = disnake.Intents().none()
intents.members = True
intents.guilds = True
intents.emojis = True
intents.messages = True
intents.message_content = True
bot = CustomClient(shard_count=2 if not IS_BETA else 1, command_prefix="$$",help_command=None, intents=intents)

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
    "BoardCommands.ClanCommands",
    "BoardCommands.TopCommands",
    "BoardCommands.FamilyCommands",
    "BoardCommands.PlayerCommands",
    "BoardCommands.Utils.Buttons",
    "BoardCommands.WarCommands",
    "Exceptions.ExceptionHandler",
    "Export.ExportsCog",
    "FamilyManagement.Reminders.Reminders",
    "FamilyManagement.bans",
    "FamilyManagement.strikes",
    "FamilyManagement.rosters",
    "Legends & Trophies.family_trophy_stats",
    "Legends & Trophies.Check.maincheck",
    "Legends & Trophies.leaderboards",
    "Link_and_Eval.link",
    "Link_and_Eval.eval",
    "Settings.settings",
    "Settings.setup",
    "Settings.autoboard",
    "Settings.addclans",
    "Ticketing.TicketCog",
    "Utility.army",
    "Utility.awards",
    "Utility.boost",
    "Utility.bases",
    "Utility.link_parsers",
    "help",
    "poster.poster",
    "other"
]

if not IS_CUSTOM and IS_BETA:
    initial_extensions += [
        "owner_commands"
    ]

if not IS_BETA and not IS_CUSTOM:
    initial_extensions += [
        "Background.reddit_recruit_feed",
        #"Background.region_lb_update"
    ]

if not IS_BETA:
    initial_extensions += [
        #"Background.Logs.auto_eval",
        "Background.Logs.ban_events",
        "Background.Logs.clan_capital_events",
        "Background.Logs.donations",
        "Background.Logs.join_leave_events",
        "Background.Logs.legend_events",
        "Background.Logs.player_upgrade_events",
        "Background.Logs.war_track",

        "Background.autoboard_loop",
        "Background.background_cache",
        "Background.clan_capital",
        "Background.legends_history",
        "Background.voicestat_loop",
        "Link_and_Eval.link_button",
        "Other.erikuh_comp",
        "discord_events",
    ]

@bot.command(name="r")
@commands.is_owner()
async def r(ctx):
    for extension in initial_extensions:
        bot.reload_extension(extension)
    await ctx.message.delete()

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
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    if not IS_BETA:
        #bot.loop.create_task(player_websocket())
        bot.loop.create_task(clan_websocket())
        bot.loop.create_task(war_websocket())
    bot.run(TOKEN)
