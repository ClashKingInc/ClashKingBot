import os
import disnake
from disnake import Client
from disnake.ext import commands
import traceback
from utils.clash import client

#db collections
usafam = client.usafam
server = usafam.server
clans = usafam.clans
whitelist = usafam.whitelist
banlist = usafam.banlist

TOKEN = os.getenv("TOKEN")
discClient = Client()
intents = disnake.Intents().all()

bot = commands.Bot(command_prefix="??", help_command=None, intents=intents,
    sync_commands_debug=False, sync_permissions=True)

initial_extensions = (
    "BackgroundLoops.autoboard_loop",
    "BackgroundLoops.leaderboards",
    "Family & Clans.bans",
    "Family & Clans.clan",
    "Family & Clans.donations",
    "Family & Clans.family",
    "Family & Clans.familystats",
    "Link & Eval.link",
    "Link & Eval.eval",
    "Setups.addclans",
    "Setups.autoboard",
    "Setups.evalsetup",
    "Setups.voice_countdowns",
    "Setups.welcome_messages",
    "Utility.army",
    "Utility.awards",
    "Utility.boost",
    "Utility.profile",
    "War & CWL.cwl",
    "War & CWL.war",
    "discord_events",
    "help",
    "other",
    "owner_commands",
    "settings"
)
for extension in initial_extensions:
    try:
        bot.load_extension(extension)
    except Exception as extension:
        traceback.print_exc()

bot.run(TOKEN)