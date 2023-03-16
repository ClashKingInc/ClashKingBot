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
from EventHub.event_websockets import player_websocket, clan_websocket, war_websocket

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

IS_BETA = False
discClient = Client()
intents = disnake.Intents().none()
intents.members = True
intents.guilds = True
intents.emojis = True
intents.messages = True
intents.message_content = True
bot = CustomClient(shard_count=2, command_prefix="$$",help_command=None, intents=intents, reload=True)

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
    "Clan.ClanCog",
    "Family_and_Clans.bans",
    "Family_and_Clans.strikes",
    "Family_and_Clans.familycog",
    "Family_and_Clans.rosters",
    "Legends & Trophies.family_trophy_stats",
    "Legends & Trophies.Check.maincheck",
    "Legends & Trophies.leaderboards",
    "Link & Eval.link",
    "Link & Eval.eval",
    "Setups.autoboard",
    "Setups.evalsetup",
    "Reminders.ReminderSetup",
    "Setups.welcome_messages",
    "Utility.army",
    "Utility.awards",
    "Utility.boost",
    "Utility.profile",
    "War & CWL.cwl",
    "War & CWL.war",
    "help",
    "other",
    "Utility.bases",
    "settings",
    "owner_commands",
    "Ticketing.TicketCog",
    "SetupNew.SetupCog",
    "Utility.link_parsers"
    #"War & CWL.war_track",
    #"War & CWL.lineups"
]

if not IS_BETA:
    initial_extensions += [
        "BackgroundCrons.autoboard_loop",
        "BackgroundCrons.voicestat_loop",
        "BackgroundCrons.region_lb_update",
        "BackgroundCrons.legends_history",
        "BackgroundCrons.reddit_recruit_feed",
        "BackgroundCrons.dm_reports",
        "BackgroundCrons.store_clan_capital",
        "Reminders.ReminderCrons",
        "EventHub.clan_capital_events",
        "EventHub.join_leave_events",
        "EventHub.ban_events",
        "EventHub.player_upgrade_events",
        "EventHub.legend_events",
        "Link & Eval.link_button",
        "War & CWL.war_track",
        "discord_events",
        "erikuh_comp",
        "Setups.addclans",
        "global_chat"
    ]


if __name__ == "__main__":
    sentry_sdk.init(
        dsn=os.getenv("DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=0.2,
        _experiments={
            "profiles_sample_rate": 0.2,
        }
    )
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    bot.loop.create_task(player_websocket())
    bot.loop.create_task(clan_websocket())
    bot.loop.create_task(war_websocket())
    bot.run(os.getenv("TOKEN"))
