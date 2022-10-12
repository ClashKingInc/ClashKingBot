import os
import disnake
from disnake import Client

import traceback
from CustomClasses.CustomBot import CustomClient

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc
from EventHub.event_websockets import player_websocket, clan_websocket, war_websocket

scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

discClient = Client()
intents = disnake.Intents().none()
intents.members = True
intents.guilds = True
intents.emojis = True
intents.guild_messages = True

bot = CustomClient(command_prefix="<@824653933347209227> ",help_command=None, intents=intents,
    sync_commands_debug=False, sync_permissions=True)

initial_extensions = (
    "BackgroundCrons.autoboard_loop",
    "BackgroundCrons.voicestat_loop",
    "BackgroundCrons.region_lb_update",
    "BackgroundCrons.legends_history",
    "BackgroundCrons.reddit_recruit_feed",
    "BackgroundCrons.youtube_base_feed",
    "BackgroundCrons.dm_reports",
    "EventHub.clan_capital_events",
    "EventHub.join_leave_events",
    "EventHub.ban_events",
    "EventHub.war_events",
    "EventHub.legend_events",
    "Family_and_Clans.bans",
    "Family_and_Clans.clancog",
    "Family_and_Clans.family",
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
   # "War & CWL.war_track",
    "discord_events",
    "help",
    "other",
    "settings",
    "owner_commands",
    "erikuh_comp"
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
