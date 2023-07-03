import os
import disnake
import traceback
import motor.motor_asyncio
import sentry_sdk
from CustomClasses.CustomBot import CustomClient
from disnake import Client
from disnake.ext import commands

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from Background.Logs.event_websockets import player_websocket, clan_websocket, war_websocket

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

IS_BETA = True
discClient = Client()
intents = disnake.Intents().none()
intents.members = True
intents.guilds = True
intents.emojis = True
intents.messages = True
intents.message_content = True
intents.presences = True
bot = CustomClient(shard_count=1, command_prefix="$$",help_command=None, intents=intents, reload=True)

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
    "FamilyManagement.bans",
    "FamilyManagement.strikes",
    "FamilyManagement.rosters",
    "Legends & Trophies.family_trophy_stats",
    "Legends & Trophies.Check.maincheck",
    #"Legends & Trophies.leaderboards",
    "Link_and_Eval.link",
    "Link_and_Eval.eval",
    "Setups.autoboard",
    "Setups.evalsetup",
    "Reminders.ReminderSetup",
    "Setups.welcome_messages",
    "Utility.army",
    "Utility.awards",
    "Utility.boost",
    #"War & CWL.cwl",
    #"War & CWL.war",
    "help",
    "other",
    "Utility.bases",
    #"settings",
    "owner_commands",
    "Ticketing.TicketCog",
    #"SetupNew.SetupCog",
    "Utility.link_parsers",
    #"War & CWL.war_track",
    #"War & CWL.lineups",
    #"Exceptions.ExceptionHandler",
    "BoardCommands.ClanCommands",
    "BoardCommands.TopCommands",
    "BoardCommands.FamilyCommands",
    "BoardCommands.PlayerCommands",
    "Export.ExportsCog",
    "BoardCommands.Utils.Buttons",
    "Background.refresh_boards",
    "BoardCommands.WarCommands",
    "Background.background_cache"
]

if not IS_BETA:
    initial_extensions += [
        "Background.autoboard_loop",
        "Background.voicestat_loop",
        "Background.region_lb_update",
        "Background.legends_history",
        "Background.reddit_recruit_feed",
        "Background.dm_reports",
        "Background.store_clan_capital",
        "Reminders.ReminderCrons",
        "EventHub.clan_capital_events",
        "EventHub.join_leave_events",
        "EventHub.ban_events",
        "EventHub.player_upgrade_events",
        "EventHub.legend_events",
        "Link_and_Eval.link_button",
        "War & CWL.war_track",
        "discord_events",
        "Other.erikuh_comp",
        "Setups.addclans",
        "global_chat"
    ]

@bot.command(name="r")
@commands.is_owner()
async def r(ctx):
    for extension in initial_extensions:
        bot.reload_extension(extension)
    await ctx.send("Reloaded all cogs")

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
        traces_sample_rate=0.2,
        _experiments={
            "profiles_sample_rate": 0.2,
        },
        before_send=before_send
    )
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    if not IS_BETA:
        bot.loop.create_task(player_websocket())
        bot.loop.create_task(clan_websocket())
        bot.loop.create_task(war_websocket())
    bot.run(os.getenv("TOKEN"))
