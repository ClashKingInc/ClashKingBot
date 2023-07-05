import asyncio

import coc
import disnake
import pytz
from ImageGen import WarEndResult as war_gen
from disnake.ext import commands
from Assets.emojiDictionary import emojiDictionary
from CustomClasses.CustomBot import CustomClient
from datetime import datetime

tiz = pytz.utc
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]
from Background.Logs.event_websockets import war_ee
from utils.war import create_reminders, schedule_war_boards, war_start_embed, main_war_page, missed_hits, store_war, update_war_message
from utils.general import create_superscript
from CustomClasses.CustomServer import DatabaseClan
from BoardCommands.Utils.War import attacks_embed, defenses_embed


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

        reminder_times = await self.bot.get_reminder_times(clan_tag=new_war.clan.tag)
        acceptable_times = self.bot.get_times_in_range(reminder_times=reminder_times, war_end_time=new_war.end_time)
        await create_reminders(bot=self.bot, clan_tag=new_war.clan.tag, times=acceptable_times)
        await schedule_war_boards(bot=self.bot, war=new_war)

        if not new_war.is_cwl:
            try:
                await self.bot.war_client.register_war(clan_tag=new_war.clan_tag)
            except:
                pass

        clan = None
        if new_war.type == "cwl":
            clan = await self.bot.getClan(new_war.clan.tag)
        war_league = clan.war_league if clan is not None else None


        for cc in await self.bot.clan_db.find( {"$and": [{"tag": new_war.clan.tag}, {"logs.war_log.webhook": {"$ne": None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.war_log

            thread = None
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        raise disnake.NotFound
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue

            if new_war.state == "preparation":
                embed = await main_war_page(bot=self.bot, war=new_war,war_league=war_league)
                embed.set_footer(text=f"{new_war.type.capitalize()} War")
                await self.bot.webhook_send(webhook=webhook, thread=thread, embed=embed)

            elif new_war.state == "inWar":
                embed = war_start_embed(new_war=new_war)
                await self.bot.webhook_send(webhook=webhook, thread=thread, embed=embed)

            elif new_war.state == "warEnded":
                embed = await main_war_page(bot=self.bot, war=new_war,war_league=war_league)
                embed.set_footer(text=f"{new_war.type.capitalize()} War")
                await self.bot.webhook_send(webhook=webhook, thread=thread, embed=embed)

                file = await war_gen.generate_war_result_image(new_war)
                await self.bot.webhook_send(webhook=webhook, thread=thread, file=file)

                missed_hits_embed = await missed_hits(bot=self.bot, war=new_war)
                if len(missed_hits_embed.fields) != 0:
                    await self.bot.webhook_send(webhook=webhook, thread=thread, embed=missed_hits_embed)
                await store_war(bot=self.bot, war=new_war)


        for cc in await self.bot.clan_db.find({"$and": [{"tag": new_war.clan.tag}, {"logs.war_panel.webhook": {"$ne": None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.war_panel
            thread = None
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        raise disnake.NotFound
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


            await update_war_message(bot=self.bot, war=new_war, db_clan=db_clan, clan=clan)


            if new_war.state == "warEnded":
                file = await war_gen.generate_war_result_image(new_war)
                await self.bot.webhook_send(webhook=webhook, thread=thread, file=file)

                missed_hits_embed = await missed_hits(bot=self.bot, war=new_war)
                if len(missed_hits_embed.fields) != 0:
                    await self.bot.webhook_send(webhook=webhook, thread=thread, embed=missed_hits_embed)
                await store_war(bot=self.bot, war=new_war)


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
            "clan" : attack.attacker.clan.tag,
            "clan_name" : attack.attacker.clan.name
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

        if attack.attacker.clan.tag == war.clan.tag:
            find_result = await self.bot.player_stats.find_one({"tag": attack.attacker.tag})
            if find_result is not None:
                season = self.bot.gen_season_date()
                _time = int(datetime.now().timestamp())
                await self.bot.player_stats.update_one({"tag": attack.attacker.tag}, {"$set": {"last_online": _time}})
                await self.bot.player_stats.update_one({"tag": attack.attacker.tag}, {"$push": {f"last_online_times.{season}": _time}})


        for cc in await self.bot.clan_db.find( {"$and": [{"tag": war.clan.tag}, {"logs.war_log.webhook": {"$ne": None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            log = db_clan.war_log

            star_str = ""
            stars = attack.stars
            for x in range(0, stars):
                star_str += self.bot.emoji.war_star.emoji_string
            for x in range(0, 3 - stars):
                star_str += self.bot.emoji.no_star.emoji_string

            if attack.attacker.clan.tag == war.clan.tag:
                hit_message = f"{self.bot.emoji.thick_sword} {emojiDictionary(attack.attacker.town_hall)}**{attack.attacker.name}{create_superscript(num=attack.attacker.map_position)}**" \
                              f" {star_str} **{attack.destruction}%** {emojiDictionary(attack.defender.town_hall)}{create_superscript(num=attack.defender.map_position)}"
            else:
                # is a defense
                hit_message = f"{self.bot.emoji.shield} {emojiDictionary(attack.defender.town_hall)}**{attack.defender.name}{create_superscript(num=attack.defender.map_position)}**" \
                              f" {star_str} **{attack.destruction}%** {emojiDictionary(attack.attacker.town_hall)}{create_superscript(num=attack.attacker.map_position)}"
            try:
                webhook = await self.bot.getch_webhook(log.webhook)
                if log.thread is not None:
                    thread = await self.bot.getch_channel(log.thread)
                    if thread.locked:
                        continue
                    await webhook.send(content=hit_message, thread=thread)
                else:
                    await webhook.send(content=hit_message)
            except (disnake.NotFound, disnake.Forbidden):
                await log.set_thread(id=None)
                await log.set_webhook(id=None)
                continue


        for cc in await self.bot.clan_db.find({"$and": [{"tag": war.clan.tag}, {"logs.war_panel.webhook": {"$ne": None}}]}).to_list(length=None):
            db_clan = DatabaseClan(bot=self.bot, data=cc)
            if db_clan.server_id not in self.bot.OUR_GUILDS:
                continue

            clan = None
            if war.type == "cwl":
                clan = await self.bot.getClan(war.clan.tag)
            await update_war_message(bot=self.bot, war=war, db_clan=db_clan, clan=clan)





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
            attack_embed: disnake.Embed = await attacks_embed(bot=self.bot, war=war)
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
            attack_embed = await defenses_embed(bot=self.bot, war=war)
            await ctx.send(embed=attack_embed, ephemeral=True)

        elif "menuforwar_" in str(ctx.data.custom_id):
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

            button = [disnake.ui.ActionRow(
                disnake.ui.Button(label="Opponent Link", style=disnake.ButtonStyle.url, url=war.opponent.share_link),
                disnake.ui.Button(label="Clash Of Stats", style=disnake.ButtonStyle.url, url=f"https://www.clashofstats.com/clans/{war.opponent.tag.strip('#')}/summary"),
                disnake.ui.Button(label="Chocolate Clash", style=disnake.ButtonStyle.url, url=f"https://fwa.chocolateclash.com/cc_n/clan.php?tag={war.opponent.tag.strip('#')}")
            )
            ]
            await ctx.send(components= button, ephemeral=True)

def setup(bot: CustomClient):
    bot.add_cog(War_Log(bot))