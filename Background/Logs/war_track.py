import asyncio

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
from Background.Logs.event_websockets import war_ee
from Exceptions.CustomExceptions import MissingWebhookPerms
import string
import random

class War_Log(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.war_ee = war_ee
        self.war_ee.on("new_war", self.new_war)
        self.war_ee.on("war_attack", self.war_attack)

    async def new_war(self, event):
        cwl_group = event.get("league_group")
        if cwl_group:
            new_war = coc.ClanWar(data=event["war"], client=self.bot.coc_client, league_group=coc.ClanWarLeagueGroup(data=cwl_group, client=self.bot.coc_client), clan_tag=event.get("clan_tag"))
        else:
            new_war = coc.ClanWar(data=event["war"], client=self.bot.coc_client, clan_tag=event.get("clan_tag"))

        cog = self.bot.get_cog(name="Reminder Cron")
        reminder_times = await self.bot.get_reminder_times(clan_tag=new_war.clan.tag)
        acceptable_times = self.bot.get_times_in_range(reminder_times=reminder_times, war_end_time=new_war.end_time)


        if new_war.state == "preparation" or new_war.state == "inWar":
            if new_war.state == "preparation":
                scheduler.add_job(self.send_or_update_war_start, 'date', run_date=new_war.start_time.time,
                                  args=[new_war.clan.tag], id=f"war_start_{new_war.clan.tag}",
                                  name=f"{new_war.clan.tag}_war_start", misfire_grace_time=None)
            scheduler.add_job(self.send_or_update_war_end, 'date', run_date=new_war.end_time.time,
                              args=[new_war.clan.tag, int(new_war.preparation_start_time.time.timestamp())], id=f"war_end_{new_war.clan.tag}",
                              name=f"{new_war.clan.tag}_war_end", misfire_grace_time=None)

        if not new_war.is_cwl:
            try:
                await self.bot.war_client.register_war(clan_tag=new_war.clan_tag)
            except:
                pass

        for clan_result in await self.bot.clan_db.find({"tag": f"{new_war.clan.tag}"}).to_list(length=500):
            if clan_result.get("war_log") is None:
                continue

            try:
                war_channel = await self.bot.getch_channel(clan_result.get("war_log"), raise_exception=True)
                feed_type = clan_result.get("attack_feed", "Update Feed")  # other is "Update Feed"
                war_cog = self.bot.get_cog(name="War")

                clan = None
                if new_war.type == "cwl":
                    clan = await self.bot.getClan(new_war.clan.tag)

                if new_war.state == "preparation":
                    if feed_type == "Update Feed":
                        await self.update_war_message(war=new_war, clan_result=clan_result, clan=clan)
                    else:
                        embed = await war_cog.main_war_page(war=new_war, clan=clan)
                        embed.set_footer(text=f"{new_war.type.capitalize()} War")
                        await war_channel.send(embed=embed)


                elif new_war.state == "inWar":
                    if feed_type == "Update Feed":
                        await self.update_war_message(war=new_war, clan_result=clan_result, clan=clan)
                    else:
                        embed = self.war_start_embed(new_war=new_war)
                        await war_channel.send(embed=embed)

                elif new_war.state == "warEnded":
                    embed = await war_cog.main_war_page(war=new_war, clan=clan)
                    embed.set_footer(text=f"{new_war.type.capitalize()} War")

                    if feed_type == "Update Feed":
                        await self.update_war_message(war=new_war, clan_result=clan_result, clan=clan)
                    else:
                        await war_channel.send(embed=embed)

                    file = await war_gen.generate_war_result_image(new_war)
                    await war_channel.send(file=file)
                    # calculate missed attacks
                    one_hit_missed = []
                    two_hit_missed = []
                    for player in new_war.clan.members:
                        if len(player.attacks) < new_war.attacks_per_member:
                            th_emoji = self.bot.fetch_emoji(name=player.town_hall)
                            if new_war.attacks_per_member - len(player.attacks) == 1:
                                one_hit_missed.append(f"{th_emoji}{player.name}")
                            else:
                                two_hit_missed.append(f"{th_emoji}{player.name}")

                    embed = disnake.Embed(title=f"{new_war.clan.name} vs {new_war.opponent.name}",
                                          description="Missed Hits", color=disnake.Color.orange())
                    if one_hit_missed:
                        embed.add_field(name="One Hit Missed", value="\n".join(one_hit_missed))
                    if two_hit_missed:
                        embed.add_field(name="Two Hits Missed", value="\n".join(two_hit_missed))
                    embed.set_thumbnail(url=new_war.clan.badge.url)
                    if len(embed.fields) != 0:
                        await war_channel.send(embed=embed)

                    await self.store_war(war=new_war)

            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                try:
                    del self.bot.feed_webhooks[clan_result.get("war_log")]
                except:
                    pass
                await self.bot.clan_db.update_one({"$and": [
                    {"tag": new_war.clan.tag},
                    {"server": clan_result.get("server")}
                ]}, {'$set': {"war_log": None}})
                continue


    async def war_attack(self, event):
        cwl_group = event.get("league_group")
        if cwl_group:
            war = coc.ClanWar(data=event["war"], client=self.bot.coc_client,
                                  league_group=coc.ClanWarLeagueGroup(data=cwl_group, client=self.bot.coc_client), clan_tag=event.get("clan_tag"))
        else:
            war = coc.ClanWar(data=event["war"], client=self.bot.coc_client, clan_tag=event.get("clan_tag"))
        attack = coc.WarAttack(data=event["attack"], client=self.bot.coc_client, war=war)

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
            "clan" : attack.attacker.clan.tag
        })

        point_to_point = {0:0, 1: 400, 2: 800, 3 : 1200}

        if str(war.type) == "cwl" or str(war.type) == "random":
            points_earned = point_to_point[attack.stars]
            if attack.stars != 0:
                if attack.defender.town_hall > attack.attacker.town_hall:
                    points_earned += (attack.defender.town_hall - attack.attacker.town_hall) * 400

            if attack.defender.town_hall < attack.attacker.town_hall:
                points_earned -= (attack.defender.town_hall - attack.attacker.town_hall) * 200
            await self.bot.player_stats.update_one({"tag": attack.attacker_tag}, {"$inc": {f"points": points_earned}})

        #is an attack
        for cc in await self.bot.clan_db.find({"tag": f"{war.clan.tag}"}).to_list(length=500):
            try:
                warlog_channel = cc.get("war_log")
                if warlog_channel is None:
                    continue

                war_channel = await self.bot.getch_channel(cc.get("war_log"), raise_exception=True)

                attack_feed = cc.get("attack_feed", "Continuous Feed")

                #only update last online if its an attack (is on the war clan side)
                if attack.attacker.clan.tag == war.clan.tag:
                    find_result = await self.bot.player_stats.find_one({"tag" : attack.attacker.tag})
                    if find_result is not None:
                        season = self.bot.gen_season_date()
                        _time = int(datetime.now().timestamp())
                        await self.bot.player_stats.update_one({"tag": attack.attacker.tag}, {"$set": {"last_online": _time}})
                        await self.bot.player_stats.update_one({"tag": attack.attacker.tag}, {"$push": {f"last_online_times.{season}": _time}})

                if attack_feed == "Continuous Feed":
                    star_str = ""
                    stars = attack.stars
                    for x in range(0, stars):
                        star_str += self.bot.emoji.war_star.emoji_string
                    for x in range(0, 3 - stars):
                        star_str += self.bot.emoji.no_star.emoji_string

                    if attack.attacker.clan.tag == war.clan.tag:
                        hit_message = f"{self.bot.emoji.thick_sword} {emojiDictionary(attack.attacker.town_hall)}**{attack.attacker.name}{self.create_superscript(num=attack.attacker.map_position)}**" \
                                      f" {star_str} **{attack.destruction}%** {emojiDictionary(attack.defender.town_hall)}{self.create_superscript(num=attack.defender.map_position)}"
                    else:
                        # is a defense
                        hit_message = f"{self.bot.emoji.shield} {emojiDictionary(attack.defender.town_hall)}**{attack.defender.name}{self.create_superscript(num=attack.defender.map_position)}**" \
                                      f" {star_str} **{attack.destruction}%** {emojiDictionary(attack.attacker.town_hall)}{self.create_superscript(num=attack.attacker.map_position)}"
                    await war_channel.send(content=hit_message)

                else:
                    clan = None
                    if war.type == "cwl":
                        clan = await self.bot.getClan(war.clan.tag)
                    await self.update_war_message(war=war, clan_result=cc, clan=clan)

            except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                await self.bot.clan_db.update_one({"server": cc.get("server")}, {'$set': {"war_log": None}})
                continue



    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "listwarattacks_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            prep_time = 0
            try:
                prep_time = int(str(ctx.data.custom_id).split('_')[1])
            except:
                pass
            war_data = await self.bot.clan_wars.find_one({"war_id" : f"{clan}-{prep_time}"})
            war = None
            if war_data is not None:
                war = coc.ClanWar(data=war_data["data"], client=self.bot.coc_client, clan_tag=clan)
            if war is None:
                war = await self.bot.war_client.war_result(clan_tag=clan, preparation_start=prep_time)
            if war is None:
                war = await self.bot.get_clanwar(clanTag=clan)
            if war is None:
                return await ctx.send(content="No War Found", ephemeral=True)
            war_cog = self.bot.get_cog(name="War")
            attack_embed: disnake.Embed = await war_cog.attacks_embed(war)
            await ctx.send(embed=attack_embed, ephemeral=True)
        elif "listwardefenses_" in str(ctx.data.custom_id):
            await ctx.response.defer(ephemeral=True)
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            prep_time = 0
            try:
                prep_time = int(str(ctx.data.custom_id).split('_')[1])
            except:
                pass
            war_data = await self.bot.clan_wars.find_one({"war_id": f"{clan}-{prep_time}"})
            war = None
            if war_data is not None:
                war = coc.ClanWar(data=war_data["data"], client=self.bot.coc_client, clan_tag=clan)
            if war is None:
                war = await self.bot.war_client.war_result(clan_tag=clan, preparation_start=prep_time)
            if war is None:
                war = await self.bot.get_clanwar(clanTag=clan)
            if war is None:
                return await ctx.send(content="No War Found", ephemeral=True)
            war_cog = self.bot.get_cog(name="War")
            attack_embed = await war_cog.defenses_embed(war)
            await ctx.send(embed=attack_embed, ephemeral=True)



def setup(bot: CustomClient):
    bot.add_cog(War_Log(bot))