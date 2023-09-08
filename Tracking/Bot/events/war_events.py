import coc
import sys
sys.path.append("..")
import settings
import asyncio



@coc.WarEvents.new_war()
async def new_war(new_war: coc.ClanWar):
    clan_tasks = []
    async def send_ws(ws, json):
        try:
            await ws.send_json(json)
        except:
            try:
                settings.WAR_CLIENTS.remove(ws)
            except:
                pass

    league_group = None
    if new_war.is_cwl and league_group is not None:
        league_group: coc.ClanWarLeagueGroup = new_war.league_group
        league_group = league_group._raw_data

    json_data = {"type": "new_war", "war": new_war._raw_data, "league_group" : league_group, "clan_tag": new_war.clan.tag}

    for client in settings.WAR_CLIENTS.copy():
        task = asyncio.ensure_future(send_ws(ws=client, json=json_data))
        clan_tasks.append(task)
    await asyncio.gather(*clan_tasks, return_exceptions=False)