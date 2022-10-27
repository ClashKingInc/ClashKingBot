from disnake.ext import commands
import disnake
from time import strftime
from time import gmtime
import pytz
tiz = pytz.utc
import coc

from CustomClasses.CustomBot import CustomClient
from EventHub.event_websockets import war_ee


class war_event(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.war_ee = war_ee
        self.war_ee.on("attack", self.attack_event)
        self.war_ee.on("state", self.state_change)

    async def attack_event(self, event):
        name = event["name"]
        opponent_name = event["opponent_name"]
        attack = event["attack"]
        clan_tag = event["war"]["clan"]["tag"]

        war = event["war"]
        clan = war["clan"]
        opponent = war["opponent"]
        opp_score = 0
        clan_score = 0
        for member in clan["members"]:
            try:
                opp_score += member["bestOpponentAttack"]["stars"]
            except:
                pass

        for member in opponent["members"]:
            try:
                clan_score += member["bestOpponentAttack"]["stars"]
            except:
                pass

        tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            warlog_channel = cc.get("war_log")
            if warlog_channel is None:
                continue

            try:
                warlog_channel = await server.fetch_channel(warlog_channel)
                if warlog_channel is None:
                    continue
            except:
                continue

            star_str = ""
            stars = attack["stars"]
            for x in range(0, stars):
                star_str += self.bot.emoji.war_star
            for x in range(0, 3-stars):
                star_str += self.bot.emoji.no_star

            duration = strftime("%M:%S", gmtime(attack["duration"]))
            if stars == 3:
                color = disnake.Color.gold()
            elif stars == 0:
                color = disnake.Color.light_grey()
            else:
                color = disnake.Color.green()
            embed = disnake.Embed(
                description=f"{self.bot.emoji.sword_clash.emoji_string} [**{name}**]({self.bot.create_link(tag=attack['attackerTag'])}) attacked [**{opponent_name}**]({self.bot.create_link(tag=attack['defenderTag'])})\n"
                            f"{star_str}{attack['destructionPercentage']}% | {self.bot.emoji.clock.emoji_string}{duration}"
                , color=color)

            embed.set_footer(icon_url=event["war"]["clan"]["badgeUrls"]["large"], text=f"{event['war']['clan']['name']} {clan_score} - {event['war']['opponent']['name']} {opp_score}")

            try:
                await warlog_channel.send(embed=embed)
            except:
                continue

    async def state_change(self, event):
        status = event["type"]
        clan_name = event["war"]["clan"]["name"]
        clan_tag = event["war"]["clan"]["tag"]
        opp_clan_name = event["war"]["opponent"]["name"]
        war = event["war"]
        clan = war["clan"]
        opponent = war["opponent"]


        if status == "preparation":
            embed = disnake.Embed(title=f"{clan_name} vs {opp_clan_name}",
                description=f"Status: In Prep"
                , color=disnake.Color.green())

        if status == "inWar":
            embed = disnake.Embed(title=f"{clan_name} vs {opp_clan_name}",
                description=f"Status: In War"
                , color=disnake.Color.green())

        if status == "warEnded":
            war = await self.bot.coc_client.get_clan_war(clan.tag)
            war_time = war.start_time.seconds_until
            war_state = "In Prep"
            war_pos = "Starting"
            if war_time >= 0:
                war_time = war.start_time.time.replace(tzinfo=tiz).timestamp()
            else:
                war_time = war.end_time.seconds_until
                if war_time <= 0:
                    war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                    war_pos = "Ended"
                    war_state = "War Over"
                else:
                    war_time = war.end_time.time.replace(tzinfo=tiz).timestamp()
                    war_pos = "Ending"
                    war_state = "In War"

            stats = await self.calculate_stars_percent(war)
            team_stars = str(stats[2]).ljust(7)
            opp_stars = str(stats[0]).rjust(7)
            team_per = (str(stats[3]) + "%").ljust(7)
            opp_per = (str(stats[1]) + "%").rjust(7)
            team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(
                7)
            opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)

            th_comps = await self.war_th_comps(war)

            embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link})",
                                  color=disnake.Color.green())
            embed.add_field(name=f"**War Against**", value=f"[**{war.opponent.name}**]({war.opponent.share_link})\n­\n",
                            inline=False)
            embed.add_field(name=f"**War State**",
                            value=f"{war_state} ({war.team_size} vs {war.team_size})\n"
                                  f"{war_pos}: <t:{int(war_time)}:R>\n­\n", inline=False)
            embed.add_field(name="**War Stats**",
                            value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                                  f"`{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                                  f"`{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n­\n"
                            , inline=False)

            embed.add_field(name="War Composition", value=f"{war.clan.name}\n{th_comps[0]}\n"
                                                          f"{war.opponent.name}\n{th_comps[1]}", inline=False)

            embed.set_thumbnail(url=clan.badge.large)

        tracked = self.bot.clan_db.find({"tag": f"{clan_tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{clan_tag}"})
        for cc in await tracked.to_list(length=limit):
            server = cc.get("server")
            try:
                server = await self.bot.fetch_guild(server)
            except:
                continue
            warlog_channel = cc.get("war_log")
            if warlog_channel is None:
                continue

            try:
                warlog_channel = await server.fetch_channel(warlog_channel)
                if warlog_channel is None:
                    continue
            except:
                continue

            try:
                await warlog_channel.send(embed=embed)
            except:
                continue


    async def calculate_stars_percent(self, war: coc.ClanWar):
        stars = 0
        destr = 0
        num_def = 0

        opp_stars = 0
        opp_destr = 0
        opp_num_def = 0

        for member in war.members:
            if member not in war.opponent.members:
                defenses = member.defenses
                num_def +=1
                largest_star = 0
                largest_per = 0
                for defense in defenses:
                    star = defense.stars
                    if star >= largest_star:
                        if defense.destruction > largest_per:
                            largest_star = star
                            largest_per = defense.destruction
                stars += largest_star
                destr += largest_per
            else:
                defenses = member.defenses
                opp_num_def += 1
                largest_star = 0
                largest_per = 0
                for defense in defenses:
                    star = defense.stars
                    if star >= largest_star:
                        if defense.destruction > largest_per:
                            largest_star = star
                            largest_per = defense.destruction
                opp_stars += largest_star
                opp_destr += largest_per

        avg_destr = round(destr/num_def, 2)
        avg_destr_opp = round(opp_destr / opp_num_def, 2)
        return [stars, avg_destr, opp_stars, avg_destr_opp]


    async def war_th_comps(self, war: coc.ClanWar):
        thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        opp_thcount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


        for player in war.members:
            th = player.town_hall

            if player not in war.opponent.members:
                count = thcount[th - 1]
                thcount[th - 1] = count + 1
            else:
                count = opp_thcount[th - 1]
                opp_thcount[th - 1] = count + 1

        stats = ""
        for x in reversed(range(len(thcount))):
            count = thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    th_emoji = self.bot.fetch_emoji(x + 1)
                    stats += f"{th_emoji}`{count} `"
                else:
                    th_emoji = self.bot.fetch_emoji(x + 1)
                    stats += f"{th_emoji}`{count} `"

        opp_stats = ""
        for x in reversed(range(len(opp_thcount))):
            count = opp_thcount[x]
            if count != 0:
                if (x + 1) <= 9:
                    th_emoji = self.bot.fetch_emoji(x + 1)
                    opp_stats += f"{th_emoji}`{count} `"
                else:
                    th_emoji = self.bot.fetch_emoji(x + 1)
                    opp_stats += f"{th_emoji}`{count} `"

        return [stats, opp_stats]

def setup(bot: CustomClient):
    bot.add_cog(war_event(bot))