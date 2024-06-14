import coc
import disnake

from background.logs.events import clan_ee
from classes.DatabaseClient.Classes.settings import DatabaseClan
from classes.bot import CustomClient
from disnake.ext import commands


class BanEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("members_join_leave", self.ban_alerts)

    async def ban_alerts(self, event):
        clan = coc.Clan(data=event["new_clan"], client=self.bot.coc_client)
        members_joined = [coc.ClanMember(data=member, client=self.bot.coc_client, clan=clan) for member in event.get("joined", [])]

        if members_joined:
            results = await self.bot.banlist.find({"VillageTag": {"$in" :  [m.tag for m in members_joined]}}).to_list(length=None)
            #members that have ban results
            for result in results:
                #go thru each banned person, and find out what server they are banned on
                ban_server_id = result.get("server")
                if ban_server_id not in self.bot.OUR_GUILDS:
                    continue

                #find the clan + server combination
                clan_result = await self.bot.clan_db.find_one({"$and": [
                    {"tag": clan.tag},
                    {"server": ban_server_id}
                ]})
                if clan_result:
                    db_clan = DatabaseClan(bot=self.bot, data=clan_result)

                    server = await self.bot.getch_guild(db_clan.server_id)
                    if server is None:
                        continue

                    member = coc.utils.get(members_joined, tag=result.get("VillageTag"))

                    notes = result.get("Notes")
                    if notes == "":
                        notes = "No Reason Given"
                    date = result.get("DateCreated")[:10]

                    role = f"<@&{db_clan.member_role}>"
                    embed = disnake.Embed(
                        description=f"{role}\n[WARNING! BANNED PLAYER {member.name} JOINED]({member.share_link})",
                        color=disnake.Color.green())
                    embed.add_field(name="Banned Player.",
                                    value=f"Player {member.name} [{member.tag}] has joined {clan.name} and is on the {server.name} BAN list!\n\n"
                                          f"Banned on: {date}\nReason: {notes}")
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/843624785560993833/932701461614313562/2EdQ9Cx.png")

                    try:
                        channel = await self.bot.getch_channel(channel_id=db_clan.ban_alert_channel or db_clan.clan_channel)
                        await channel.send(content=role, embed=embed)
                    except (disnake.NotFound, disnake.Forbidden):
                        if db_clan.ban_alert_channel is None:
                            await db_clan.set_clan_channel(id=None)
                        else:
                            await db_clan.set_ban_alert_channel(id=None)
                        continue


def setup(bot: CustomClient):
    bot.add_cog(BanEvents(bot))