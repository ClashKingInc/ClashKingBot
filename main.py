import os

import discord
from discord import Client
from discord.ext import commands
from discord_slash import SlashCommand
import traceback
from HelperMethods.clashClient import client, pingToRole, coc_client

#db collections
usafam = client.usafam
server = usafam.server
clans = usafam.clans
whitelist = usafam.whitelist
banlist = usafam.banlist

TOKEN = os.getenv("TOKEN")
discClient = Client()
intents = discord.Intents().all()

async def get_prefix(bot, message):
    results = await server.find_one({"server": message.guild.id})
    prefix = results.get("prefix")
    return prefix

bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, help_command=None, intents=intents)
slash = SlashCommand(bot, sync_commands=True)

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


@bot.event
async def on_guild_join(guild):
    results = await server.find_one({"server": guild.id})
    if results is  None:
        await server.insert_one({
            "server": guild.id,
            "prefix" : ".",
            "banlist" : None,
            "greeting" : None,
            "cwlcount" : None,
            "topboardchannel" : None,
            "tophour": None,
            "lbboardChannel": None,
            "lbhour": None
        })
    channel = bot.get_channel(937519135607373874)
    await channel.send(f"Just joined {guild.name}")

@bot.event
async def on_command(ctx):
    channel = bot.get_channel(936069304946929727)
    server = ctx.guild.name
    user = ctx.author
    command = ctx.message.content
    embed = discord.Embed(description=f"**{command}** \nused by {user.mention} [{user.name}] in {server} server",
                           color=discord.Color.blue())
    embed.set_thumbnail(url=user.avatar_url)
    await channel.send(embed=embed)

def check_commands():
    async def predicate(ctx):
        member = ctx.author
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
            else:
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
    con = con.replace(f"{curr_prefix}", "")
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
    "War.warevents"
)

for extension in initial_extensions:
    try:
        bot.load_extension(extension)
    except Exception as extension:
        traceback.print_exc()

bot.run(TOKEN)