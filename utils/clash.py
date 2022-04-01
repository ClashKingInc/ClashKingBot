import os
import coc

from dotenv import load_dotenv
load_dotenv()

COC_EMAIL = os.getenv("COC_EMAIL")
COC_PASSWORD = os.getenv("COC_PASSWORD")
DB_LOGIN = os.getenv("DB_LOGIN")
LINK_API_USER = os.getenv("LINK_API_USER")
LINK_API_PW = os.getenv("LINK_API_PW")

from disnake import utils

coc_client = coc.login(COC_EMAIL, COC_PASSWORD, client=coc.EventsClient, key_count=10, key_names="DiscordBot", throttle_limit = 25)
import certifi
ca = certifi.where()

import motor.motor_asyncio
client = motor.motor_asyncio.AsyncIOMotorClient(DB_LOGIN)
import disnake
#from coc_client import utils
from coc.ext import discordlinks

link_client = discordlinks.login(LINK_API_USER, LINK_API_PW)

async def player_handle(ctx, tag):
  try:
    clashPlayer = await coc_client.get_player(tag)
  except:
    embed = disnake.Embed(description=f"{tag} is not a valid player tag.",
                          color=disnake.Color.red())
    return await ctx.send(embed=embed)

async def getTags(ctx, ping):
  if (ping.startswith('<@') and ping.endswith('>')):
    ping = ping[2:len(ping) - 1]

  if (ping.startswith('!')):
    ping = ping[1:len(ping)]
  id = ping
  tags = await link_client.get_linked_players(id)
  return tags

async def getPlayer(playerTag):
  #print(playerTag)
  try:
    #print("here")
    clashPlayer = await coc_client.get_player(playerTag)
    #print(clashPlayer.name)
    return clashPlayer
  except:
    return None

async def getClan(clanTag):
  try:
    clan = await coc_client.get_clan(clanTag)
    return clan
  except:
    return None

async def verifyPlayer(playerTag, playerToken):
  verified = await coc_client.verify_player_token(playerTag, playerToken)
  return verified


async def getClanWar(clanTag):
  try:
    war = await coc_client.get_clan_war(clanTag)
    return war
  except:
    return None

async def pingToMember(ctx, ping):
  ping = str(ping)
  if (ping.startswith('<@') and ping.endswith('>')):
    ping = ping[2:len(ping) - 1]

  if (ping.startswith('!')):
    ping = ping[1:len(ping)]

  try:
    member = await ctx.guild.fetch_member(ping)
    return member
  except:
    return None


async def pingToRole(ctx, ping):
    ping = str(ping)
    if (ping.startswith('<@') and ping.endswith('>')):
        ping = ping[2:len(ping) - 1]

    if (ping.startswith('&')):
        ping = ping[1:len(ping)]

    try:
      roles = await ctx.guild.fetch_roles()
      role = utils.get(roles, id=int(ping))
      return role
    except:
        return None

async def pingToChannel(ctx, ping):
  ping = str(ping)
  if (ping.startswith('<#') and ping.endswith('>')):
    ping = ping[2:len(ping) - 1]

  try:
    channel =  ctx.guild.get_channel(int(ping))
    return channel
  except:
    return None
