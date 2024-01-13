import coc
import sys
sys.path.append("..")
import settings
import asyncio



@coc.RaidEvents.raid_attack()
async def raid_attack(old_member: coc.RaidMember, new_member: coc.RaidMember, raid: coc.RaidLogEntry):
    clan_tasks = []

    async def send_ws(ws, json):
        try:
            await ws.send_json(json)
        except:
            try:
                settings.RAID_CLIENTS.remove(ws)
            except:
                pass

    json_data = {"type": "raid_attacks",
                 "clan_tag" : raid.clan_tag,
                 "old_member": old_member._raw_data,
                 "new_member": new_member._raw_data,
                 "raid": raid._raw_data}

    for client in settings.RAID_CLIENTS.copy():
        task = asyncio.ensure_future(send_ws(ws=client, json=json_data))
        clan_tasks.append(task)
    await asyncio.gather(*clan_tasks, return_exceptions=False)


@coc.RaidEvents.state()
async def state(old_raid: coc.RaidLogEntry, raid: coc.RaidLogEntry):
    clan_tasks = []

    async def send_ws(ws, json):
        try:
            await ws.send_json(json)
        except:
            try:
                settings.RAID_CLIENTS.remove(ws)
            except:
                pass

    json_data = {"type": "raid_state", "clan_tag" : raid.clan_tag, "old_raid": old_raid._raw_data, "raid": raid._raw_data}

    for client in settings.RAID_CLIENTS.copy():
        task = asyncio.ensure_future(send_ws(ws=client, json=json_data))
        clan_tasks.append(task)
    await asyncio.gather(*clan_tasks, return_exceptions=False)