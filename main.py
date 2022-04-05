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

async def get_prefix(bot, message):
    results = await server.find_one({"server": message.guild.id})
    prefix = results.get("prefix")
    if message.guild.id == 810466565744230410:
        return [prefix, "."]
    return prefix

bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, help_command=None, intents=intents,
    sync_commands_debug=True, sync_permissions=True, test_guilds=[923764211845312533, 548297912443207706, 810466565744230410, 767590042675314718, 869306654640984075, 505168702732369922, 659528917849341954])

@bot.event
async def on_ready():
  tags = []
  tracked = clans.find()
  limit = await clans.count_documents(filter={})

  for tClan in await tracked.to_list(length=limit):
      tag = tClan.get("tag")
      tags.append(tag)

  coc_client.add_clan_updates(*tags)

  for g in bot.guilds:
      results = await server.find_one({"server": g.id})
      if results is None:
          await server.insert_one({
              "server": g.id,
              "prefix": ".",
              "banlist": None,
              "greeting": None,
              "cwlcount": None,
              "topboardchannel": None,
              "tophour": None,
              "lbboardChannel": None,
              "lbhour": None
          })

  print(f'We have logged in')


@bot.command(name='reload', hidden=True)
async def _reload(ctx, *, module : str):
    """Reloads a module."""
    if ctx.message.author.id == 706149153431879760:
        try:
            bot.unload_extension(module)
            bot.load_extension(module)
        except:
            await ctx.send('<a:no:862552093324083221> Could not reload module.')
        else:
            await ctx.send('<a:check:861157797134729256> Reloaded module successfully')
    else:
        await ctx.send("You aren't magic. <:PS_Noob:783126177970782228>")

@bot.command(name='leave')
@commands.is_owner()
async def leaveg(ctx, *, guild_name):
    guild = disnake.utils.get(bot.guilds, name=guild_name)  # Get the guild by name
    if guild is None:
        await ctx.send("No guild with that name found.")  # No guild found
        return
    await guild.leave()  # Guild found
    await ctx.send(f"I left: {guild.name}!")





@bot.event
async def on_command(ctx):
    channel = bot.get_channel(936069304946929727)
    server = ctx.guild.name
    user = ctx.author
    command = ctx.message.content
    embed = disnake.Embed(description=f"**{command}** \nused by {user.mention} [{user.name}] in {server} server",
                           color=disnake.Color.blue())
    embed.set_thumbnail(url=user.avatar_url)
    #await channel.send(embed=embed)

def check_commands():
    async def predicate(ctx):
        member = ctx.author
        if member.id == 821610755718774814:
            return True
        commandd = ctx.command.qualified_name
        print(commandd)
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
        for role in await results.to_list(length=limit):
            role = role.get("role")
            role = await pingToRole(ctx,role)
            if member in role.members:
                return True
        return False
    return commands.check(predicate)

@bot.event
async def on_message(message):

    prefixes = await get_prefix(bot, message)
    has_prefix = False
    curr_prefix = ""
    for prefix in prefixes:
        if message.content.startswith(prefix):
            has_prefix=True
            curr_prefix = prefix
            break

    if has_prefix==False:
        return await bot.process_commands(message)

    con = message.content
    con = con.lower()
    con = con.replace(f"{curr_prefix}", "",1)
    results = await clans.find_one({"$and": [
            {"alias": con},
            {"server": message.guild.id}
        ]})

    if results == None:
        return await bot.process_commands(message)


    tag = results.get("tag")
    #print(tag)
    message.content = f"{curr_prefix}getclan {tag}"
    await bot.process_commands(message)


@bot.command(name='serverm')
@commands.is_owner()
async def serversmm(ctx):
    text = ""
    guilds = bot.guilds
    for guild in guilds:
        name = guild.name
        text += f"{name} | {len(guild.members)}\n"

    embed = disnake.Embed(title=f"{len(guilds)} servers",description=text,
                          color=disnake.Color.green())

    await ctx.send(embed=embed)

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
    "Link & Eval.onjoin",
    "Family & Clans.addclans",
    "Family & Clans.family",
    "Family & Clans.getclan",
    "evalsetup"

)
for extension in initial_extensions:
    try:
        bot.load_extension(extension)
    except Exception as extension:
        traceback.print_exc()

bot.run(TOKEN)