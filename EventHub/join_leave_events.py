from disnake.ext import commands
import disnake
from utils.troop_methods import heros, heroPets
from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import clan_ee
from utils.troop_methods import leagueAndTrophies

class join_leave_events(commands.Cog, name="Clan Join & Leave Events"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on("memberList", self.join_leave_events)

    async def join_leave_events(self, event):
        previous_members = event["old_clan"]["memberList"]
        current_members = event["new_clan"]["memberList"]
        clan_tag = event["new_clan"]["tag"]

        curr_tags = [member["tag"] for member in current_members]
        prev_tag = [member["tag"] for member in previous_members]

        new_tags = list(set(curr_tags).difference(prev_tag))
        left_tags = list(set(prev_tag).difference(curr_tags))

        async for player in self.bot.coc_client.get_players(new_tags):
            tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
            limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
            for cc in await tracked.to_list(length=limit):
                server = cc.get("server")
                try:
                    server = await self.bot.fetch_guild(server)
                except:
                    continue
                joinlog_channel = cc.get("joinlog")
                if joinlog_channel is None:
                    continue
                try:
                    joinlog_channel = await server.fetch_channel(joinlog_channel)
                except (disnake.Forbidden, disnake.NotFound):
                    await self.bot.clan_db.update_one({"$and": [
                        {"tag": clan_tag},
                        {"server": server.id}
                    ]}, {'$set': {"joinlog": None}})

                if joinlog_channel is None:
                    continue

                hero = heros(player)
                pets = heroPets(player)
                if hero is None:
                    hero = ""
                else:
                    hero = f"{hero}"

                if pets is None:
                    pets = ""
                else:
                    pets = f"{pets}"

                th_emoji = self.bot.fetch_emoji(player.town_hall)
                embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                                  f"**{th_emoji}{player.town_hall} {leagueAndTrophies(player)} <:star:825571962699907152>{player.war_stars} {hero}**\n"
                                      , color=disnake.Color.green())
                embed.set_footer(icon_url=event["new_clan"]["badgeUrls"]["large"], text=f"Joined {event['new_clan']['name']} [{event['new_clan']['members']}/50]")
                try:
                    await joinlog_channel.send(embed=embed)
                except:
                    continue

        async for player in self.bot.coc_client.get_players(left_tags):
            tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
            limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
            for cc in await tracked.to_list(length=limit):
                server = cc.get("server")
                try:
                    server = await self.bot.fetch_guild(server)
                except:
                    continue
                joinlog_channel = cc.get("joinlog")
                if joinlog_channel is None:
                    continue
                try:
                    joinlog_channel = await server.fetch_channel(joinlog_channel)
                except (disnake.Forbidden, disnake.NotFound):
                    await self.bot.clan_db.update_one({"$and": [
                        {"tag": clan_tag},
                        {"server": server.id}
                    ]}, {'$set': {"joinlog": None}})

                if joinlog_channel is None:
                    continue

                hero = heros(player)
                pets = heroPets(player)
                if hero is None:
                    hero = ""
                else:
                    hero = f"{hero}"

                if pets is None:
                    pets = ""
                else:
                    pets = f"{pets}"

                th_emoji = self.bot.fetch_emoji(player.town_hall)
                embed = disnake.Embed(description=f"[**{player.name}** ({player.tag})]({player.share_link})\n" +
                                                  f"**{th_emoji}{player.town_hall} {leagueAndTrophies(player)} <:star:825571962699907152>{player.war_stars} {hero}**\n"
                                      , color=disnake.Color.red())

                if player.clan is not None:
                    #rclan = await self.bot.getClan(player.clan.tag)
                    embed.set_footer(icon_url=player.clan.badge.url,
                                     text=f"Left {event['new_clan']['name']} [{event['new_clan']['members']}/50] and Joined {player.clan.name}")
                else:
                    embed.set_footer(icon_url=event["new_clan"]["badgeUrls"]["large"],
                                     text=f"Left {event['new_clan']['name']} [{event['new_clan']['members']}/50]")


                try:
                    await joinlog_channel.send(embed=embed)
                except:
                    continue

def setup(bot: CustomClient):
    bot.add_cog(join_leave_events(bot))