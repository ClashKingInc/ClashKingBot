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

        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        if limit == 0:
            return

        curr_tags = [member["tag"] for member in current_members]
        prev_tag = [member["tag"] for member in previous_members]

        tag_to_name = {}
        tag_to_share_link = {}
        current_donated_dict = {}
        current_received_dict = {}
        for member in current_members:
            tag_to_share_link[member["tag"]] = f"https://link.clashofclans.com/en?action=OpenPlayerProfile&tag=%23{member['tag'].strip('#')}"
            tag_to_name[member["tag"]] = member["name"]
            current_donated_dict[member["tag"]] = member["donations"]
            current_received_dict[member["tag"]] = member["donationsReceived"]

        donated = {}
        received = {}
        for member in previous_members:
            if member["tag"] in list(tag_to_name.keys()):
                current_donation = current_donated_dict[member["tag"]]
                current_received = current_received_dict[member["tag"]]
                change_dono = current_donation - member["donations"]
                change_rec = current_received - member["donationsReceived"]
                if change_dono > 0:
                    donated[member["tag"]] = change_dono
                if change_rec > 0:
                    received[member["tag"]] = change_rec

        clan_share_link = f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{event['new_clan']['tag'].strip('#')}"
        embed = disnake.Embed(description=f"[**{event['new_clan']['name']}**]({clan_share_link})")
        embed.set_thumbnail(url=event['new_clan']["badgeUrls"]["large"])

        donation_text = ""
        for tag, donation in donated.items():
            donation = f"{donation}".ljust(3)
            donation_text += f"<:warwon:932212939899949176>`{donation}` | [**{tag_to_name[tag]}**]({tag_to_share_link[tag]})\n"

        if donation_text != "":
            embed.add_field(name="Donated", value=donation_text, inline=False)

        received_text = ""
        for tag, donation in received.items():
            donation = f"{donation}".ljust(3)
            received_text += f"<:warlost:932212154164183081>`{donation}` | [**{tag_to_name[tag]}**]({tag_to_share_link[tag]})\n"

        if received_text != "":
            embed.add_field(name="Received", value=received_text, inline=False)

        if donation_text != "" or received_text != "":
            tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
            for cc in await tracked.to_list(length=limit):
                server = cc.get("server")
                donolog_channel = cc.get("donolog")
                if donolog_channel is None:
                    continue
                try:
                    donolog_channel = await self.bot.fetch_channel(donolog_channel)
                except (disnake.Forbidden, disnake.NotFound):
                    await self.bot.clan_db.update_one({"$and": [
                        {"tag": clan_tag},
                        {"server": server}
                    ]}, {'$set': {"donolog": None}})

                if donolog_channel is None:
                    continue

                try:
                    await donolog_channel.send(embed=embed)
                except:
                    continue

        new_tags = list(set(curr_tags).difference(prev_tag))
        left_tags = list(set(prev_tag).difference(curr_tags))

        #if anyone joined or left, fetch clan, get channel then go thru the players & send embeds
        if new_tags or left_tags:
            tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
            for cc in await tracked.to_list(length=limit):
                server = cc.get("server")
                joinlog_channel = cc.get("joinlog")
                if joinlog_channel is None:
                    continue
                try:
                    joinlog_channel = await self.bot.fetch_channel(joinlog_channel)
                except (disnake.Forbidden, disnake.NotFound):
                    await self.bot.clan_db.update_one({"$and": [
                        {"tag": clan_tag},
                        {"server": server}
                    ]}, {'$set': {"joinlog": None}})

                if joinlog_channel is None:
                    continue
                async for player in self.bot.coc_client.get_players(new_tags):
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
                        # rclan = await self.bot.getClan(player.clan.tag)
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