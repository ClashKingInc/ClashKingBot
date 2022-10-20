
from disnake.ext import commands
import disnake
from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import clan_ee

class BanEvents(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("memberList", self.ban_alerts)

    async def ban_alerts(self, event):
        previous_members = event["old_clan"]["memberList"]
        current_members = event["new_clan"]["memberList"]
        clan_tag = event["new_clan"]["tag"]

        curr_tags = [member["tag"] for member in current_members]
        prev_tag = [member["tag"] for member in previous_members]

        new_tags = list(set(curr_tags).difference(prev_tag))

        if not new_tags:
            return

        for tag in new_tags:
            results = await self.bot.banlist.find_one({"VillageTag": tag})
            if results is not None:
                tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
                limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
                for cc in await tracked.to_list(length=limit):
                    server = cc.get("server")
                    name = cc.get("name")
                    try:
                        server = await self.bot.fetch_guild(server)
                    except:
                        continue

                    results = await self.bot.banlist.find_one({"$and": [
                        {"VillageTag": tag},
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

                        player = await self.bot.getPlayer(tag)

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