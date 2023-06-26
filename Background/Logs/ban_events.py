
from disnake.ext import commands
import disnake
import coc
from CustomClasses.CustomBot import CustomClient
from Background.Logs.event_websockets import clan_ee

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
            tracked = self.bot.clan_db.find({"tag": f"{clan.tag}"})
            limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan.tag}"})
            for cc in await tracked.to_list(length=limit):
                name = cc.get("name")

                server = await self.bot.getch_guild(cc.get("server"))
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
                    date = results.get("DateCreated")
                    date = date[:10]
                    channel = cc.get("ban_alert_channel")
                    if channel is None:
                        channel = cc.get("clanChannel")

                    role = cc.get("generalRole")

                    role = server.get_role(role)
                    channel = self.bot.get_channel(channel)

                    player = await self.bot.getPlayer(member.tag)

                    embed = disnake.Embed(
                        description=f"[WARNING! BANNED PLAYER {player.name} JOINED]({player.share_link})",
                        color=disnake.Color.green())
                    embed.add_field(name="Banned Player.",
                                    value=f"Player {player.name} [{player.tag}] has joined {name} and is on the {server.name} BAN list!\n\n"
                                          f"Banned on: {date}\nReason: {notes}")
                    embed.set_thumbnail(
                        url="https://cdn.discordapp.com/attachments/843624785560993833/932701461614313562/2EdQ9Cx.png")
                    await channel.send(content=role.mention, embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(BanEvents(bot))