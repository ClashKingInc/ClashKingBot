import os
import disnake
import traceback
import motor.motor_asyncio

from CustomClasses.CustomBot import CustomClient
from disnake import Client
from disnake.ext import commands

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from EventHub.event_websockets import player_websocket, clan_websocket

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
bot = CustomClient(command_prefix="$$",help_command=None, intents=intents, reload=True)

def check_commands():
    async def predicate(ctx: disnake.ApplicationCommandInteraction):
        if ctx.author.id == 706149153431879760:
            return True
        db_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
        whitelist = db_client.usafam.whitelist
        member = ctx.author

        commandd = ctx.application_command.qualified_name
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


if IS_BETA:
    initial_extensions = (
        #"BackgroundCrons.autoboard_loop",
        #"BackgroundCrons.voicestat_loop",
        #"BackgroundCrons.region_lb_update",
        #"BackgroundCrons.legends_history",
        #"BackgroundCrons.reddit_recruit_feed",
        #"BackgroundCrons.dm_reports",
        #"BackgroundCrons.store_clan_capital",
        #"BackgroundCrons.reminders",
        #"EventHub.clan_capital_events",
        #"EventHub.join_leave_events",
        #"EventHub.ban_events",
        #"EventHub.player_upgrade_events",
        #"EventHub.legend_events",
        "Family_and_Clans.bans",
        "Family_and_Clans.clancog",
        "Family_and_Clans.familycog",
        "Legends & Trophies.family_trophy_stats",
        "Legends & Trophies.Check.maincheck",
        "Legends & Trophies.leaderboards",
        "Link & Eval.link",
        "Link & Eval.eval",
        #"Link & Eval.link_button",
        "Setups.addclans",
        "Setups.autoboard",
        "Setups.evalsetup",
        "Setups.voice_countdowns",
        "Setups.welcome_messages",
        #"Setups.clan_boards",
        "Utility.army",
        "Utility.awards",
        "Utility.boost",
        "Utility.profile",
        "War & CWL.cwl",
        "War & CWL.war",
        #"War & CWL.war_track",
        #"discord_events",
        "help",
        "other",
        "settings",
        "owner_commands",
        #"erikuh_comp",
        "Family_and_Clans.rosters",
        #"global_chat"
    )
else:
    initial_extensions = (
    "BackgroundCrons.autoboard_loop",
    "BackgroundCrons.voicestat_loop",
    "BackgroundCrons.region_lb_update",
    "BackgroundCrons.legends_history",
    "BackgroundCrons.reddit_recruit_feed",
    "BackgroundCrons.dm_reports",
    "BackgroundCrons.store_clan_capital",
    "BackgroundCrons.reminders",
    "EventHub.clan_capital_events",
    "EventHub.join_leave_events",
    "EventHub.ban_events",
    "EventHub.player_upgrade_events",
    "EventHub.legend_events",
    "Family_and_Clans.bans",
    "Family_and_Clans.clancog",
    "Family_and_Clans.familycog",
    "Family_and_Clans.rosters",
    "Legends & Trophies.family_trophy_stats",
    "Legends & Trophies.Check.maincheck",
    "Legends & Trophies.leaderboards",
    "Link & Eval.link",
    "Link & Eval.eval",
    "Link & Eval.link_button",
    "Setups.addclans",
    "Setups.autoboard",
    "Setups.evalsetup",
    "Setups.voice_countdowns",
    "Setups.welcome_messages",
    #"Setups.clan_boards",
    "Utility.army",
    "Utility.awards",
    "Utility.boost",
    "Utility.profile",
    "War & CWL.cwl",
    "War & CWL.war",
    "War & CWL.war_track",
    "discord_events",
    "help",
    "other",
    "settings",
    "owner_commands",
    "erikuh_comp",
    "global_chat"
    )


if __name__ == "__main__":
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as extension:
            traceback.print_exc()
    bot.loop.create_task(player_websocket())
    bot.loop.create_task(clan_websocket())
    bot.run(os.getenv("TOKEN"))
