import coc
import disnake

from background.logs.events import clan_ee
from classes.server import DatabaseClan
from classes.bot import CustomClient
from disnake.ext import commands


class BanEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("member_join", self.ban_alerts)

    async def ban_alerts(self, event):
        clan = coc.Clan(data=event["clan"], client=self.bot.coc_client)
        member = coc.ClanMember(data=event["member"], client=self.bot.coc_client, clan=clan)

        results = await self.bot.banlist.find_one({"VillageTag": member.tag})
        if results is not None:
            for cc in await self.bot.clan_db.find({"tag": f"{clan.tag}"}).to_list(length=None):
                db_clan = DatabaseClan(bot=self.bot, data=cc)
                if db_clan.server_id not in self.bot.OUR_GUILDS:
                    continue
                server = await self.bot.getch_guild(db_clan.server_id)
                if server is None:
                    continue

                results = await self.bot.banlist.find_one({"$and": [
                    {"VillageTag": member.tag},
                    {"server": server.id}
                ]})

                if results is not None:
                    notes = results.get("Notes")
                    if notes == "":
                        notes = "No Reason Given"
                    date = results.get("DateCreated")[:10]

                    role = f"<@&{db_clan.member_role}>"
                    embed = disnake.Embed(
                        description=f"{role}\n[WARNING! BANNED PLAYER {member.name} JOINED]({member.share_link})",
                        color=disnake.Color.green())
                    embed.add_field(name="Banned Player.",
                                    value=f"Player {member.name} [{member.tag}] has joined {clan.name} and is on the {server.name} BAN list!\n\n"
                                          f"Banned on: {date}\nReason: {notes}")
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/843624785560993833/932701461614313562/2EdQ9Cx.png")

                    try:
                        channel = await self.bot.getch_channel(channel_id=db_clan.clan_channel if db_clan.ban_alert_channel is None else db_clan.ban_alert_channel)
                        await channel.send(content=role, embed=embed)
                    except (disnake.NotFound, disnake.Forbidden):
                        if db_clan.ban_alert_channel is None:
                            await db_clan.set_clan_channel(id=None)
                        else:
                            await db_clan.set_ban_alert_channel(id=None)
                        continue


def setup(bot: CustomClient):
    bot.add_cog(BanEvents(bot))