import os

import disnake
from disnake import Client
from disnake.ext import commands
import traceback
from utils.clash import client, pingToRole, coc_client

#db collections
usafam = client.usafam
server = usafam.server
clans = usafam.clans
whitelist = usafam.whitelist
banlist = usafam.banlist

TOKEN = os.getenv("TOKEN")
discClient = Client()
intents = disnake.Intents().all()

bot = commands.Bot(command_prefix=".", help_command=None, intents=intents,
    sync_commands_debug=True, sync_permissions=True, test_guilds=[923764211845312533, 548297912443207706, 810466565744230410, 767590042675314718, 869306654640984075, 505168702732369922, 659528917849341954])



'''
initial_extensions = (
    "Bans.banevent",
    "Bans.banlist",
    "Boards.autoboard",
    "Boards.leaderboards",
    "Boards.top",
    "Family & Clans.addclans",
    "cwl",
    "Family & Clans.family",
    "Family & Clans.getclan",
    "HelperMethods.search",
    "Link & Eval.eval",
    "Link & Eval.link",
    "Link & Eval.onjoin",
    "Miscellaneous.army",
    "Miscellaneous.awards",
    "Miscellaneous.boost",
    "Miscellaneous.help",
    "Miscellaneous.misc",
    "Profile.profile",
    "Profile.profile_stats",
    "Profile.profile_troops",
    "Profile.profile_history",
    "Profile.pagination",
    "ProfilePic.pfp",
    "RoleManagement.evalignore",
    "RoleManagement.removeroles",
    "RoleManagement.linkremoverole",
    "RoleManagement.generalrole",
    "RoleManagement.whitelist",
    "rosters",
    "roster_class",
    "War.warevents",
    "voice_countdowns",
    "War.war",
    "War.war_ping",
    "clansettings",
    "donations",
    "loc"
)
'''

initial_extensions = (
    "Bans.banevent",
    "Bans.banlist",
    "Profile.profile",
    "Boards.autoboard",
    "Boards.leaderboards",
    "Boards.top",
    "Link & Eval.eval",
    "Link & Eval.link",
    "Link & Eval.onjoin",
    "Family & Clans.addclans",
    "Family & Clans.family",
    "Family & Clans.getclan",
    "evalsetup",
    "Miscellaneous.army",
    "Miscellaneous.awards",
    "Miscellaneous.boost",
    "discord_events",
    "owner_commands"

)
for extension in initial_extensions:
    try:
        bot.load_extension(extension)
    except Exception as extension:
        traceback.print_exc()

bot.run(TOKEN)