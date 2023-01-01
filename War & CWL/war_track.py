
import coc
import disnake
import pytz
from ImageGen import WarEndResult as war_gen
from disnake.ext import commands
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from datetime import datetime
from main import scheduler
tiz = pytz.utc
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]

class War_Log(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.bot.coc_client.add_events(self.new_war, self.war_attack)

    @coc.WarEvents.state_or_new_war()
    async def new_war(self, old_war: coc.ClanWar, new_war: coc.ClanWar):
        #store old war
        #self.bot.store_war(old_war)
        #send notif that a new war started
        #print("new_war")
        tracked = self.bot.clan_db.find({"tag": f"{new_war.clan.tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{new_war.clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            try:
                warlog_channel = cc.get("war_log")
                if warlog_channel is None:
                    continue
                try:
                    warlog_channel = await self.bot.fetch_channel(warlog_channel)
                    if warlog_channel is None:
                        continue
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.clan_db.update_one({"$and": [
                                {"tag": new_war.clan.tag},
                                {"server": cc.get("server")}
                                ]}, {'$set': {"war_log": None}})
                    continue
                attack_feed = cc.get("attack_feed")
                war_message = cc.get("war_message")
                war_id = cc.get("war_id")

                if new_war.state == "preparation" or (f"{old_war.clan.tag}-{int(old_war.preparation_start_time.time.timestamp())}" != f"{new_war.clan.tag}-{int(new_war.preparation_start_time.time.timestamp())}"):
                    cog = self.bot.get_cog(name="Reminder Cron")
                    reminder_times = await self.bot.get_reminder_times(clan_tag=new_war.clan.tag)
                    acceptable_times = self.bot.get_times_in_range(reminder_times=reminder_times,
                                                                   war_end_time=new_war.end_time)
                    if acceptable_times:
                        for time in acceptable_times:
                            reminder_time = time[0] / 3600
                            if reminder_time.is_integer():
                                reminder_time = int(reminder_time)
                            send_time = time[1]
                            scheduler.add_job(cog.war_reminder, 'date', run_date=send_time,
                                              args=[new_war.clan.tag, reminder_time],
                                              id=f"{reminder_time}_{new_war.clan.tag}", name=f"{new_war.clan.tag}",
                                              misfire_grace_time=None)
                    if not new_war.is_cwl:
                        try:
                            await self.bot.war_client.register_war(clan_tag=new_war.clan_tag)
                        except:
                            pass

                if new_war.state == "preparation":
                    #if we skipped from one war to next, update the old one
                    if old_war.state == "inWar":
                        if attack_feed is None:
                            attack_feed = "Continuous Feed"
                        if attack_feed == "Continuous Feed":
                            war_state = "Ended"
                            war_pos = "War Over"
                            war_time = old_war.end_time.time.replace(tzinfo=tiz).timestamp()

                            war_cog = self.bot.get_cog(name="War")
                            stats = await war_cog.calculate_stars_percent(old_war)
                            if stats[2] > stats[0]:
                                result = "War Won"
                            elif stats[2] == stats[0]:
                                if stats[3] > stats[1]:
                                    result = "War Won"
                                else:
                                    result = "War Lost"
                            else:
                                result = "War Lost"
                            team_stars = str(stats[2]).ljust(7)
                            opp_stars = str(stats[0]).rjust(7)
                            team_per = (str(stats[3]) + "%").ljust(7)
                            opp_per = (str(stats[1]) + "%").rjust(7)
                            team_hits = f"{len(old_war.attacks) - len(old_war.opponent.attacks)}/{old_war.team_size * old_war.attacks_per_member}".ljust(
                                7)
                            opp_hits = f"{len(old_war.opponent.attacks)}/{old_war.team_size * old_war.attacks_per_member}".rjust(
                                7)

                            embed = disnake.Embed(description=f"[**{old_war.clan.name}**]({old_war.clan.share_link})",
                                                  color=disnake.Color.red())
                            embed.add_field(name=f"**War Against**",
                                            value=f"[**{old_war.opponent.name}**]({old_war.opponent.share_link})\n­\n",
                                            inline=False)
                            embed.add_field(name=f"**{result}**",
                                            value=f"{war_state} ({old_war.team_size} vs {old_war.team_size})\n"
                                                  f"{war_pos}: <t:{int(war_time)}:R>\n­\n", inline=False)
                            embed.add_field(name="**War Stats**",
                                            value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                                                  f"`{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                                                  f"`{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n­"
                                            , inline=False)

                            embed.set_thumbnail(url=old_war.clan.badge.large)
                            embed.set_footer(text=f"{old_war.type.capitalize()} War")
                            await warlog_channel.send(embed=embed)
                        else:
                            await self.update_war_message(war=old_war, warlog_channel=warlog_channel,
                                                          message_id=war_message, server=cc.get("server"))

                    clan = await self.bot.getClan(new_war.clan.tag)
                    war_cog = self.bot.get_cog(name="War")
                    embed = await war_cog.main_war_page(war=new_war, clan=clan)
                    embed.set_footer(text=f"{new_war.type.capitalize()} War")

                    button = []
                    if attack_feed == "Update Feed":
                        button = [disnake.ui.ActionRow(
                            disnake.ui.Button(label="Attacks", emoji=self.bot.emoji.sword_clash.partial_emoji,
                                              style=disnake.ButtonStyle.grey,
                                              custom_id=f"listwarattacks_{new_war.clan.tag}"),
                            disnake.ui.Button(label="Defenses", emoji=self.bot.emoji.shield.partial_emoji,
                                              style=disnake.ButtonStyle.grey,
                                              custom_id=f"listwardefenses_{new_war.clan.tag}"))]

                    message = await warlog_channel.send(embed=embed, components=button)
                    war_id = f"{new_war.clan.tag}v{new_war.opponent.tag}-{int(new_war.start_time.time.timestamp())}"
                    await self.bot.clan_db.update_one({"$and": [{"tag": new_war.clan.tag},{"server": cc.get("server")}]}, {'$set': {"war_message": message.id, "war_id" : war_id}})

                if new_war.state == "inWar":

                    if attack_feed is None:
                        attack_feed = "Continuous Feed"
                    if attack_feed == "Continuous Feed":
                        embed = disnake.Embed(description=f"[**{new_war.clan.name}**]({new_war.clan.share_link})",
                                              color=disnake.Color.yellow())
                        embed.add_field(name=f"**War Started Against**",
                                        value=f"[**{new_war.opponent.name}**]({new_war.opponent.share_link})\n­",
                                        inline=False)
                        embed.set_thumbnail(url=new_war.clan.badge.large)
                        embed.set_footer(text=f"{new_war.type.capitalize()} War")
                        await warlog_channel.send(embed=embed)
                    else:
                        if old_war.state == "warEnded":
                            clan = await self.bot.getClan(new_war.clan.tag)
                            war_cog = self.bot.get_cog(name="War")
                            embed = await war_cog.main_war_page(war=new_war, clan=clan)
                            embed.set_footer(text=f"{new_war.type.capitalize()} War")

                            button = []
                            if attack_feed == "Update Feed":
                                button = [disnake.ui.ActionRow(
                                    disnake.ui.Button(label="Attacks", emoji=self.bot.emoji.sword_clash.partial_emoji,
                                                      style=disnake.ButtonStyle.grey,
                                                      custom_id=f"listwarattacks_{new_war.clan.tag}"),
                                    disnake.ui.Button(label="Defenses", emoji=self.bot.emoji.shield.partial_emoji,
                                                      style=disnake.ButtonStyle.grey,
                                                      custom_id=f"listwardefenses_{new_war.clan.tag}"))]
                            message = await warlog_channel.send(embed=embed, components=button)
                        else:
                            await self.update_war_message(war=new_war, warlog_channel=warlog_channel, message_id=war_message, server=cc.get("server"), war_id=war_id)

                if new_war.state == "warEnded":
                    if attack_feed is None:
                        attack_feed = "Continuous Feed"
                    if attack_feed == "Continuous Feed":
                        war_state = "Ended"
                        war_pos = "War Over"
                        war_time = new_war.end_time.time.replace(tzinfo=tiz).timestamp()

                        war_cog = self.bot.get_cog(name="War")
                        stats = await war_cog.calculate_stars_percent(new_war)
                        if stats[2] > stats[0]:
                            result = "War Won"
                        elif stats[2] == stats[0]:
                            if stats[3] > stats[1]:
                                result = "War Won"
                            else:
                                result = "War Lost"
                        else:
                            result = "War Lost"
                        team_stars = str(stats[2]).ljust(7)
                        opp_stars = str(stats[0]).rjust(7)
                        team_per = (str(stats[3]) + "%").ljust(7)
                        opp_per = (str(stats[1]) + "%").rjust(7)
                        team_hits = f"{len(new_war.attacks) - len(new_war.opponent.attacks)}/{new_war.team_size * new_war.attacks_per_member}".ljust(
                            7)
                        opp_hits = f"{len(new_war.opponent.attacks)}/{new_war.team_size * new_war.attacks_per_member}".rjust(
                            7)

                        embed = disnake.Embed(description=f"[**{new_war.clan.name}**]({new_war.clan.share_link})",
                                              color=disnake.Color.red())
                        embed.add_field(name=f"**War Against**",
                                        value=f"[**{new_war.opponent.name}**]({new_war.opponent.share_link})\n­\n",
                                        inline=False)
                        embed.add_field(name=f"**{result}**",
                                        value=f"{war_state} ({new_war.team_size} vs {new_war.team_size})\n"
                                              f"{war_pos}: <t:{int(war_time)}:R>\n­\n", inline=False)
                        embed.add_field(name="**War Stats**",
                                        value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                                              f"`{team_stars}`<:star:825571962699907152>`{opp_stars}`\n"
                                              f"`{team_per}`<:broken_sword:944896241429540915>`{opp_per}`\n­"
                                        , inline=False)

                        embed.set_thumbnail(url=new_war.clan.badge.large)
                        embed.set_footer(text=f"{new_war.type.capitalize()} War")
                        await warlog_channel.send(embed=embed)
                    else:
                        await self.update_war_message(war=new_war, warlog_channel=warlog_channel, message_id=war_message, server=cc.get("server"), war_id=war_id)
                    
                    file = await war_gen.generate_war_result_image(new_war)
                    await warlog_channel.send(file=file)
                    #calculate missed attacks
                    one_hit_missed = []
                    two_hit_missed = []
                    for player in new_war.members:
                        if player not in new_war.opponent.members:
                            if len(player.attacks) < new_war.attacks_per_member:
                                th_emoji = self.bot.fetch_emoji(name=player.town_hall)
                                if new_war.attacks_per_member - len(player.attacks) == 1:
                                    one_hit_missed.append(f"{th_emoji}{player.name}")
                                else:
                                    two_hit_missed.append(f"{th_emoji}{player.name}")

                    embed = disnake.Embed(title=f"{new_war.clan.name} vs {new_war.opponent.name}", description="Missed Hits", color=disnake.Color.orange())
                    if one_hit_missed:
                        embed.add_field(name="One Hit Missed", value="\n".join(one_hit_missed))
                    if two_hit_missed:
                        embed.add_field(name="Two Hits Missed", value="\n".join(two_hit_missed))
                    embed.set_thumbnail(url=new_war.clan.badge.url)
                    if len(embed.fields) != 0:
                        await warlog_channel.send(embed=embed)

            except:
                continue


    @coc.WarEvents.war_attack()
    async def war_attack(self, attack: coc.WarAttack, war: coc.ClanWar):
        current_time = int(datetime.now().timestamp())
        await self.bot.warhits.insert_one({
            "tag" : attack.attacker.tag,
            "name" : attack.attacker.name,
            "townhall" : attack.attacker.town_hall,
            "_time" : current_time,
            "destruction" : attack.destruction,
            "stars" : attack.stars,
            "fresh" : attack.is_fresh_attack,
            "war_start" : int(war.preparation_start_time.time.timestamp()),
            "defender_tag" : attack.defender.tag,
            "defender_name" : attack.defender.name,
            "defender_townhall" : attack.defender.town_hall,
            "war_type" : str(war.type),
            "war_status" : str(war.status),
            "attack_order" : attack.order,
            "map_position" : attack.attacker.map_position,
            "war_size" : war.team_size,
            "clan" : war.clan_tag
        })

        #is an attack
        tracked = self.bot.clan_db.find({"tag": f"{war.clan.tag}"})
        limit = await self.bot.clan_db.count_documents(filter={"tag": f"{war.clan.tag}"})
        for cc in await tracked.to_list(length=limit):
            try:
                warlog_channel = cc.get("war_log")
                if warlog_channel is None:
                    continue
                try:
                    warlog_channel = await self.bot.fetch_channel(warlog_channel)
                    if warlog_channel is None:
                        continue
                except (disnake.NotFound, disnake.Forbidden):
                    await self.bot.clan_db.update_one({"server": cc.get("server")}, {'$set': {"war_log": None}})
                    continue
                attack_feed = cc.get("attack_feed")
                war_message = cc.get("war_message")
                war_id = cc.get("war_id")

                #only update last online if its an attack (is on the war clan side)
                if attack.attacker.clan.tag == war.clan.tag:
                    find_result = await self.bot.player_stats.find_one({"tag" : attack.attacker.tag})
                    if find_result is not None:
                        season = self.bot.gen_season_date()
                        _time = int(datetime.now().timestamp())
                        await self.bot.player_stats.update_one({"tag": attack.attacker.tag}, {"$set": {"last_online": _time}})
                        await self.bot.player_stats.update_one({"tag": attack.attacker.tag}, {"$push": {f"last_online_times.{season}": _time}})

                if attack_feed is None:
                    attack_feed = "Continuous Feed"
                if attack_feed == "Continuous Feed":
                    star_str = ""
                    stars = attack.stars
                    for x in range(0, stars):
                        star_str += self.bot.emoji.war_star.emoji_string
                    for x in range(0, 3 - stars):
                        star_str += self.bot.emoji.no_star.emoji_string

                    if attack.is_fresh_attack:
                        fresh_emoji = self.bot.emoji.yes
                    else:
                        fresh_emoji = self.bot.emoji.no
                    war_cog = self.bot.get_cog(name="War")
                    stats = await war_cog.calculate_stars_percent(war)

                    if attack.attacker.clan.tag == war.clan.tag:
                        hit_message = f"{self.bot.emoji.thick_sword} {emojiDictionary(attack.attacker.town_hall)}**{attack.attacker.name}{self.create_superscript(num=attack.attacker.map_position)}**" \
                                      f" {star_str} **{attack.destruction}%** {emojiDictionary(attack.defender.town_hall)}{self.create_superscript(num=attack.defender.map_position)}"
                    else:
                        # is a defense
                        hit_message = f"{self.bot.emoji.shield} {emojiDictionary(attack.defender.town_hall)}**{attack.defender.name}{self.create_superscript(num=attack.defender.map_position)}**" \
                                      f" {star_str} **{attack.destruction}%** {emojiDictionary(attack.attacker.town_hall)}{self.create_superscript(num=attack.attacker.map_position)}"
                    await warlog_channel.send(content=hit_message)
                else:
                    await self.update_war_message(war=war, warlog_channel=warlog_channel, message_id=war_message, server=cc.get("server"), war_id=war_id)
            except Exception as e:
                e = e[0:2000]
                channel = await self.bot.fetch_channel(923767060977303552)
                await channel.send(content= e)


    async def update_war_message(self, war: coc.ClanWar, warlog_channel, message_id, server, war_id):
        if war_id != f"{war.clan.tag}v{war.opponent.tag}-{int(war.start_time.time.timestamp())}":
            message_id = None
        clan = None
        if war.type == "cwl":
            clan = await self.bot.getClan(war.clan.tag)
        warlog_channel: disnake.TextChannel
        war_cog = self.bot.get_cog(name="War")
        embed = await war_cog.main_war_page(war=war, clan=clan)
        try:
            message = await warlog_channel.fetch_message(message_id)
            await message.edit(embed=embed)
        except:
            button = [disnake.ui.ActionRow(
                disnake.ui.Button(label="Attacks", emoji=self.bot.emoji.sword_clash.partial_emoji,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"listwarattacks_{war.clan.tag}"),
                disnake.ui.Button(label="Defenses", emoji=self.bot.emoji.shield.partial_emoji,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id=f"listwardefenses_{war.clan.tag}"))]
            message = await warlog_channel.send(embed=embed, components=button)
            war_id = f"{war.clan.tag}v{war.opponent.tag}-{int(war.start_time.time.timestamp())}"
            await self.bot.clan_db.update_one({"$and": [{"tag": war.clan.tag},{"server": server}]}, {'$set': {"war_message": message.id, "war_id": war_id}})

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "listwarattacks_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            war = await self.bot.get_clanwar(clan)
            war_cog = self.bot.get_cog(name="War")
            attack_embed = await war_cog.attacks_embed(war)
            await ctx.send(embed=attack_embed, ephemeral=True)
        elif "listwardefenses_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            war = await self.bot.get_clanwar(clan)
            war_cog = self.bot.get_cog(name="War")
            attack_embed = await war_cog.defenses_embed(war)
            await ctx.send(embed=attack_embed, ephemeral=True)

    def create_superscript(self, num):
        digits = [int(num) for num in str(num)]
        new_num = ""
        for d in digits:
            new_num += SUPER_SCRIPTS[d]

        return new_num

def setup(bot: CustomClient):
    bot.add_cog(War_Log(bot))