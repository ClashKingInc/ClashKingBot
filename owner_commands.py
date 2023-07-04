import json
import time
from numerize import numerize
import coc
import disnake
import pytz
from disnake.ext import commands
from datetime import datetime, timedelta
clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
import asyncio
from typing import List
from CustomClasses.CustomBot import CustomClient
from pymongo import UpdateOne
from PIL import Image, ImageDraw, ImageFont
import io
from io import BytesIO
#import chat_exporter
from ImageGen import WarEndResult as war_gen
from ImageGen import ClanCapitalResult as capital_gen
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
import aiohttp
from msgspec.json import decode
from msgspec import Struct
from coc.raid import RaidLogEntry
from collections import defaultdict
import operator
from Assets.thPicDictionary import thDictionary
import calendar
war_leagues = json.load(open(f"Assets/war_leagues.json"))
from Assets.emojiDictionary import emojiDictionary
from utils.discord_utils import interaction_handler
from utils.ClanCapital import calc_raid_medals

from urllib import request
leagues = ["Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]
from chat_exporter.construct.assets.embed import Embed
import string
import random
import os

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
import pandas as pd
from CustomClasses.CustomPlayer import MyCustomPlayer
from utils.constants import TOWNHALL_LEVELS
import numpy as np
from utils.war import create_reminders
from main import scheduler
from FamilyManagement.Reminders import SendReminders

class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #self.bot.coc_client.add_events(self.member_attack)
        self.count = 0

    @commands.Cog.listener()
    async def on_connect(self):
        print("connected")


    @commands.message_command(name="emoji_creator")
    async def emoji_creator(self, ctx: disnake.MessageCommandInteraction, message: disnake.Message):
        await ctx.response.defer(ephemeral=True)
        if len([m for m in message.attachments if "image" in m.content_type]) == 0:
            return await ctx.send(content="No Images")

        created = ""
        for pic in message.attachments:
            if "image" in pic.content_type:
                emoji = await ctx.guild.create_custom_emoji(name=pic.filename.split(".")[0], image=(await pic.read()))
                created += f"{emoji} - `<:{emoji.name}:{emoji.id}>`\n"
        await ctx.send(content=created)

    @commands.slash_command(name="test")
    @commands.is_owner()
    async def test(self, ctx: disnake.ApplicationCommandInteraction):

        emojis = {
            "Barbarian King": "<:BarbarianKing:701626158181122210>",
            "Archer Queen": "<:ArcherQueen:701626158487175270>",
            "Grand Warden": "<:GrandWarden:701933765450268672>",
            "Royal Champion": "<:RoyalChampion:701933810648088606>",
            "Battle Copter": "<:battle_copter:1109716293696888852>",
            "Electrofire Wizard": "<:electro_wiz:1109716130735587358>",
            "Archer": "<:Archer:701626909498409040>",
            "Baby Dragon": "<:BabyDragon:701626909586358364>",
            "Barbarian": "<:Barbarian:701626910207115274>",
            "Bowler": "<:Bowler:701626910614093844>",
            "Electro Dragon": "<:ElectroDragon:701626910735728672>",
            "Dragon": "<:Dragon:701626910752374804>",
            "Dragon Rider": "<:dragon_rider:855686522653114399>",
            "Balloon": "<:Balloon:701626912241352745>",
            "Ice Golem": "<:IceGolem:701626913701101668>",
            "Miner": "<:Miner:701626913793245255>",
            "Hog Rider": "<:HogRider:701626914506276895>",
            "Yeti": "<:Yeti:701626914816655431>",
            "Wizard": "<:Wizard:701626914841821186>",
            "Healer": "<:Healer:701626914930163783>",
            "Giant": "<:Giant:701626915026370671>",
            "Goblin": "<:Goblin:701626915165044828>",
            "Witch": "<:Witch:701626915173433385>",
            "Minion": "<:Minion:701626915311583294>",
            "P.E.K.K.A": "<:PEKKA:701626915328491610>",
            "Wall Breaker": "<:WallBreaker:701626915357982742>",
            "Golem": "<:Golem:701626915395600394>",
            "Lava Hound": "<:LavaHound:701626915479355483>",
            "Valkyrie": "<:Valkyrie:701626915680681994>",
            "Headhunter": "<:Headhunter:742121658386481262>",
            "Super Wall Breaker": "<:SuperWallBreaker:701626916133666896>",
            "Super Barbarian": "<:SuperBarbarian:701626916087529673>",
            "Super Archer": "<:SuperArcher:750010593045643355>",
            "Super Giant": "<:SuperGiant:701626915902980197>",
            "Sneaky Goblin": "<:SneakyGoblin:701626916129734787>",
            "Rocket Balloon": "<:RocketBalloon:854368171682431006>",
            "Super Wizard": "<:SuperWizard:785536616864153610>",
            "Super Miner": "<:sminer:1051845657910071346>",
            "Inferno Dragon": "<:InfernoDragon:742121658386743366>",
            "Super Minion": "<:SuperMinion:771375748916576286>",
            "Super Valkyrie": "<:SuperValkyrie:771375748815519825>",
            "Super Witch": "<:SuperWitch:742121660324511818>",
            "Ice Hound": "<:IceHound:785539963068481546>",
            "Super Dragon": "<:SuperDragon:918876075809964072>",
            "Super Bowler": "<:SuperBowler:892035736168185876>",
            "Unicorn": "<:Unicorn:830510531483795516>",
            "Mighty Yak": "<:MightyYak:830510531222962278>",
            "Electro Owl": "<:ElectroOwl:830511434269982790>",
            "L.A.S.S.I": "<:LASSI:830510531168829521>",
            "trophy": "<:trophyy:849144172698402817>",
            "Wall Wrecker": "<:WallWrecker:701628825142034482>",
            "Battle Blimp": "<:BattleBlimp:701628824395317328>",
            "Stone Slammer": "<:StoneSlammer:701628824688918588>",
            "Siege Barracks": "<:SiegeBarracks:701628824651169913>",
            "Log Launcher": "<:LogLauncher:785540240358113312>",
            "Flame Flinger": "<:FlameFlinger:918875579904847873>",
            "Skeleton Spell": "<:skel:652161148241707029>",
            "Rage Spell": "<:rs:665562307606347822>",
            "Poison Spell": "<:ps:652161145582387210>",
            "Healing Spell": "<:hs:652161148057026580>",
            "Invisibility Spell": "<:invi:785474117414551582>",
            "Jump Spell": "<:js:652161148032122897>",
            "Lightning Spell": "<:ls:726648294461407441>",
            "Haste Spell": "<:haste:652161145125470208>",
            "Freeze Spell": "<:fs:652161149193682974>",
            "Earthquake Spell": "<:es:652161143975968798>",
            "Bat Spell": "<:bat:652161147679670301>",
            "Clone Spell": "<:cs:652161148958801920>",
            "clan castle": "<:clan_castle:855688168816377857>",
            "shield": "<:clash:855491735488036904>",
            "Electro Titan": "<:ElectroTitan:1029213693021519963>",
            "Battle Drill": "<:BattleDrill:1029199490038628442>",
            "Recall Spell": "<:recall:1029199491385012304>",
            "Frosty": "<:Frosty:1029199487849201785>",
            "Poison Lizard": "<:PoisonLizard:1029199485450068029>",
            "Phoenix": "<:Phoenix:1029199486347661343>",
            "Diggy": "<:Diggy:1029199488906170428>",
            1: "<:02:701579364483203133>",
            2: "<:02:701579364483203133>",
            3: "<:03:701579364600643634>",
            4: "<:04:701579365850284092>",
            5: "<:05:701579365581848616>",
            6: "<:06:701579365573459988>",
            7: "<:07:701579365598756874>",
            8: "<:08:701579365321801809>",
            9: "<:09:701579365389041767>",
            10: "<:10:701579365661671464>",
            11: "<:11:701579365699551293>",
            12: "<:12:701579365162418188>",
            13: "<:132:704082689816395787>",
            14: "<:14:828991721181806623>",
            15: "<:th15_big:1029215029486157855>",
            "Capital Gold": "<:capitalgold:987861320286216223>",
            "Capital_Hall7": "<:CH7:1029590574031970434>",
            "District_Hall4": "<:DH4:1029590574900195358>",
            "District_Hall5": "<:DH5:1029590575701299301>",
            "District_Hall3": "<:DH3:1029590576879915079>",
            "District_Hall2": "<:DH2:1029590577865568297>",
            "District_Hall1": "<:DH1:1029590578721206292>",
            "Capital_Hall9": "<:CH9:1029590579279040543>",
            "Capital_Hall10": "<:CH10:1029590580583485482>",
            "Capital_Hall8": "<:CH8:1029590581602693170>",
            "Capital_Hall6": "<:CH6:1029590582533828659>",
            "Capital_Hall4": "<:CH4:1029590583645315254>",
            "Capital_Hall5": "<:CH5:1029590584819728425>",
            "Capital_Hall3": "<:CH3:1029590585864093726>",
            "Capital_Hall2": "<:CH2:1029590586795229264>",
            "Capital_Hall1": "<:CH1:1029590587298557995>",
            "Bomber": "<:Bomber:701625279562383410>",
            "Hog Glider": "<:HogGlider:701625283354296331>",
            "Cannon Cart": "<:CannonCart:701625284847206400>",
            "Power P.E.K.K.A": "<:SuperPEKKA:701625285031886941>",
            "Boxer Giant": "<:BoxerGiant:701625285061115915>",
            "Drop Ship": "<:DropShip:701625285061115955>",
            "Beta Minion": "<:BetaMinion:701625285069504562>",
            "Raged Barbarian": "<:RagedBarbarian:701625285107515462>",
            "Night Witch": "<:NightWitch:701625285161910372>",
            "Sneaky Archer": "<:SneakyArcher:701625285279219765>",
            "Battle Machine": "<:bm:1041499330240053352>",
            "Super Hog Rider": "<:SHogRider:1120604618100060180>",
            "Apprentice Warden": "<:Apprentice:1120604620713107507>"
        }

        await ctx.guild.fetch_emojis()

        new_emoji_dict = {}
        for name, emoji_name in emojis.items():
            print(name)
            if name == 15:
                continue
            emoji = self.bot.partial_emoji_gen(emoji_name)
            emoji = self.bot.get_emoji(emoji.id)
            if emoji is None:
                print(f"COULDNT FIND {name}")
                continue
            emoji_list = ctx.guild.emojis
            can_find = disnake.utils.get(emoji_list, name=emoji.name)
            if can_find is not None:
                new_emoji_dict[name] = f"<:{can_find.name}:{can_find.id}>"
                continue


            try:
                find = await ctx.guild.fetch_emoji(emoji.id)
            except:
                emoji = await ctx.guild.create_custom_emoji(name=emoji.name, image=(await emoji.read()))

            new_emoji_dict[name] = f"<:{emoji.name}:{emoji.id}>"


        print(new_emoji_dict)





    @commands.slash_command(name="migrate", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def migrate(self, ctx: disnake.ApplicationCommandInteraction):
        special = ["legend_log"]
        fields = ["joinlog", "clan_capital",  "donolog", "upgrade_log", "ban_alert_channel", "war_log"]
        cursor = self.bot.clan_db.find({"tag" : "#2JGYRJVL"})
        channel_to_webhook = {}
        field_to_new = {"joinlog" : ["join_log", "leave_log"], "clan_capital" : ["capital_donations", "capital_attacks", "raid_map", "capital_weekly_summary", "new_raid_panel"],
                        "donolog" : ["donation_log"], "upgrade_log" : ["super_troop_boost", "role_change", "troop_upgrade", "th_upgrade", "league_change", "spell_upgrade", "hero_upgrade", "name_change"],
                         "war_log" : ["war_log", "war_panel"]}
        bot_av = self.bot.user.avatar.read().close()
        for document in await cursor.to_list(length=100):
            new_json = {

            }
            id = document.get("_id")
            for field in fields:
                channel = document.get(field)
                webhook = channel_to_webhook.get(channel)
                thread = None
                if channel is not None:
                    if webhook is None:
                        try:
                            g_channel = await self.bot.getch_channel(channel, raise_exception=True)
                            if isinstance(channel, disnake.Thread):
                                webhooks = await channel.parent.webhooks()
                            else:
                                webhooks = await channel.webhooks()
                            webhook = next((w for w in webhooks if w.user.id == self.bot.user.id), None)
                            if webhook is None:
                                if isinstance(g_channel, disnake.Thread):
                                    thread = channel
                                    webhook = await g_channel.parent.create_webhook(name="ClashKing", avatar=bot_av, reason="ClashKing Clan Logs")
                                else:
                                    webhook = await g_channel.create_webhook(name="ClashKing", avatar=bot_av, reason="ClashKing Clan Logs")
                            channel_to_webhook[g_channel.id] = webhook.id
                            webhook = webhook.id
                        except:
                            webhook = None
                    else:
                        g_channel = await self.bot.getch_channel(channel, raise_exception=True)
                        if isinstance(g_channel, disnake.Thread):
                            thread = channel
                for new_field in field_to_new.get(field):
                    new_json[new_field] = {}
                    new_json[new_field]["webhook"] = webhook
                    new_json[new_field]["thread"] = thread
                    if field == "joinlog":
                        new_json[new_field]["ban_button"] = document.get("strike_ban_buttons", False)
                        new_json[new_field]["strike_button"] = document.get("strike_ban_buttons", False)
                        new_json[new_field]["profile_button"] = document.get("strike_ban_buttons", False)
                    if field == "war_log":
                        panel = document.get("attack_feed") == "Update Feed"
                        if panel and new_field == "war_log":
                            new_json[new_field]["webhook"] = None

                        if not panel and new_field == "war_panel":
                            new_json[new_field]["webhook"] = None

                        if panel and new_field == "war_panel":
                            new_json[new_field]["war_id"] = document.get("war_id")
                            new_json[new_field]["war_message"] = document.get("war_message")

            for f in ["legend_log_attacks", "legend_log_defenses"]:
                new_json[f] = {}
                new_json[f]["webhook"] = document.get("legend_log", {}).get("webhook")
                new_json[f]["thread"] = document.get("legend_log", {}).get("thread")

            server_greeting = await self.bot.server_db.find_one({"server" : document.get("server")})
            if server_greeting is not None:
                new_json["greeting"] = server_greeting.get("greeting", "")

            await self.bot.clan_db.update_one({"_id" : id}, {"$set" : {"logs" : new_json}})


    async def contribution_history(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        text = ""
        pipeline = [
            {"$match": {"$and" : [{"type" : "clanCapitalContributions"}, {"clan" : "#2GYQ02JYP"}]}},
            {"$sort": {"time": -1}},
            {"$limit" : 150},
            {"$lookup": {"from": "player_stats", "localField": "tag", "foreignField": "tag", "as": "name"}},
            {"$set": {"name": "$name.name"}}
        ]
        results = await self.bot.player_history.aggregate(pipeline).to_list(length=None)
        missing = 0
        add = 0
        for result in results:
            if result.get("p_value") is None:
                missing += 1
                continue
            diff = result.get("value") - result.get("p_value", 0)
            name = result.get("name")[0]
            text += f"<t:{result.get('time')}:R> {diff} {name}\n"
            add += 1
            if add == 25 or result == results[-1]:
                embed = disnake.Embed(description=text)
                await ctx.channel.send(embed=embed)
                add = 0; text = ""


    @commands.slash_command(name="owner_anniversary", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def anniversary(self, ctx: disnake.ApplicationCommandInteraction):
        guild = ctx.guild
        await ctx.send(content="Starting")
        msg = await ctx.channel.send("Editing 0 Members")
        x = 0
        twelve_month = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
        nine_month = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
        six_month = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
        three_month = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
        for member in guild.members:
            if member.bot:
                continue
            if x % 25 == 0:
                await msg.edit(f"Editing {x} Members")
            year = member.joined_at.year
            month = member.joined_at.month
            n_year = datetime.now().year
            n_month = datetime.now().month
            num_months = (n_year - year) * 12 + (n_month - month)
            if num_months >= 12:
                if twelve_month not in member.roles:
                    await member.add_roles(*[twelve_month])
                if nine_month in member.roles or six_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[nine_month, six_month, three_month])
            elif num_months >= 9:
                if nine_month not in member.roles:
                    await member.add_roles(*[nine_month])
                if twelve_month in member.roles or six_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[twelve_month, six_month, three_month])
            elif num_months >= 6:
                if six_month not in member.roles:
                    await member.add_roles(*[six_month])
                if twelve_month in member.roles or nine_month in member.roles or three_month in member.roles:
                    await member.remove_roles(*[twelve_month, nine_month, three_month])
            elif num_months >= 3:
                if three_month not in member.roles:
                    await member.add_roles(*[three_month])
                if twelve_month in member.roles or nine_month in member.roles or six_month in member.roles:
                    await member.remove_roles(*[twelve_month, nine_month, six_month])
            x += 1
        await ctx.channel.send(content="Done")


    @commands.slash_command(name="raid-map", description="See the live raid map", guild_ids=[923764211845312533])
    async def raid_map(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
        await ctx.response.defer()
        clan = await self.bot.getClan(clan_tag=clan)
        weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
        weekend_raid_entry = await get_raidlog_entry(clan=clan, weekend=weekend, bot=self.bot, limit=1)
        current_clan = weekend_raid_entry.attack_log[-1]

        background = Image.open("ImageGen/RaidMap.png")
        draw = ImageDraw.Draw(background)

        capital_names = ImageFont.truetype("ImageGen/SCmagic.ttf", 27)
        league_name_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 35)

        paste_spot = {"Capital Peak" : (1025, 225), "Barbarian Camp" : (1360, 500), "Wizard Valley" : (1025, 675),
                      "Balloon Lagoon" : (750, 920), "Builder's Workshop" : (1250, 970)}
        text_spot = {"Wizard Valley" : (1128, 655), "Balloon Lagoon" : (845, 900), "Builder's Workshop" : (1300, 920)}
        for spot, district in enumerate(current_clan.districts):
            name = "District_Hall"
            if district.id == 70000000:
                name = "Capital_Hall"
            if district.id not in [70000000, 70000001]:
                draw.text(text_spot.get(district.name, (100, 100)), district.name, anchor="mm", fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0), font=capital_names)

            name = f"{name}{district.hall_level}"
            district_image = Image.open(f"ImageGen/CapitalDistricts/{name}.png")
            size = 212, 200
            district_image = district_image.resize(size, Image.ANTIALIAS)
            area = paste_spot.get(district.name, (100, 106))
            background.paste(district_image, area, district_image.convert("RGBA"))

        def save_im(background):
            # background.show()
            temp = io.BytesIO()
            #background = background.resize((725, 471))
            # background = background.resize((1036, 673))
            background.save(temp, format="png", compress_level=1)
            temp.seek(0)
            file = disnake.File(fp=temp, filename="filename.png")
            temp.close()
            return file

        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(None, save_im, background)

        await ctx.send(file=file)

    @commands.slash_command(name="cwl-image", description="Image showing cwl rankings & th comps",
                            guild_ids=[923764211845312533])
    async def testthis(self, ctx: disnake.ApplicationCommandInteraction, clan: str):
        await ctx.response.defer()
        tag = clan
        try:
            base_clan = await self.bot.getClan(clan_tag=tag)
            cwl: coc.ClanWarLeagueGroup = await self.bot.coc_client.get_league_group(clan_tag=base_clan.tag)
        except:
            return await ctx.send(content="Clan not in cwl")

        background = Image.open("ImageGen/cwlbk.png")
        clan_name = ImageFont.truetype("ImageGen/SCmagic.ttf", 30)
        league_name_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 35)
        numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 35)
        small_numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 15)
        stat_numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 25)
        perc_numbers = ImageFont.truetype("ImageGen/SCmagic.ttf", 20)

        draw = ImageDraw.Draw(background)
        stroke = 4
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_obj = defaultdict(str)

        for round in cwl.rounds:
            for war_tag in round:
                war = await self.bot.coc_client.get_league_war(war_tag)
                war: coc.ClanWar
                if str(war.status) == "won":
                    star_dict[war.clan.tag] += 10
                elif str(war.status) == "lost":
                    star_dict[war.opponent.tag] += 10
                tag_to_obj[war.clan.tag] = war.clan
                tag_to_obj[war.opponent.tag] = war.opponent
                star_dict[war.clan.tag] += war.clan.stars
                for attack in war.clan.attacks:
                    dest_dict[war.clan.tag] += attack.destruction
                star_dict[war.opponent.tag] += war.opponent.stars
                for attack in war.opponent.attacks:
                    dest_dict[war.opponent.tag] += attack.destruction

        star_list = []
        for tag, stars in star_dict.items():
            destruction = dest_dict[tag]
            clan_obj = tag_to_obj[tag]
            star_list.append([clan_obj, stars, destruction])

        sorted_clans = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)

        for count, _ in enumerate(sorted_clans):
            clan = _[0]
            stars = _[1]
            destruction = _[2]
            clan: coc.ClanWarLeagueClan

            async def fetch(url, session):
                async with session.get(url) as response:
                    image_data = BytesIO(await response.read())
                    return image_data

            tasks = []
            async with aiohttp.ClientSession() as session:
                tasks.append(fetch(clan.badge.medium, session))
                responses = await asyncio.gather(*tasks)
                await session.close()

            for image_data in responses:
                badge = Image.open(image_data)
                size = 100, 100
                badge.thumbnail(size, Image.ANTIALIAS)
                background.paste(badge, (200, 645 + (105 * count)), badge.convert("RGBA"))
            if clan.tag == base_clan.tag:
                color = (136, 193, 229)
            else:
                color = (255, 255, 255)
            draw.text((315, 690 + (106 * count)), f"{clan.name[:17]}", anchor="lm", fill=color, stroke_width=stroke,
                      stroke_fill=(0, 0, 0), font=clan_name)
            promo = [x["promo"] for x in war_leagues["items"] if x["name"] == base_clan.war_league.name][0]
            demo = [x["demote"] for x in war_leagues["items"] if x["name"] == base_clan.war_league.name][0]
            extra = 0
            if count + 1 <= promo:
                placement_img = Image.open("ImageGen/league_badges/2168_0.png")
                color = (166, 217, 112)
            elif count + 1 >= demo:
                placement_img = Image.open("ImageGen/league_badges/2170_0.png")
                color = (232, 16, 17)
            else:
                placement_img = Image.open("ImageGen/league_badges/2169_0.png")
                extra = 15
                color = (255, 255, 255)

            draw.text((100, 690 + (106 * count)), f"{count + 1}.", anchor="lm", fill=color, stroke_width=stroke,
                      stroke_fill=(0, 0, 0), font=numbers)
            size = 100, 100
            placement_img.thumbnail(size, Image.ANTIALIAS)
            background.paste(placement_img, (30, 663 + (107 * count) + extra), placement_img.convert("RGBA"))

            thcount = defaultdict(int)

            for player in clan.members:
                thcount[player.town_hall] += 1
            spot = 0
            for th_level, th_count in sorted(thcount.items(), reverse=True):
                e_ = ""
                if th_level >= 13:
                    e_ = "-2"
                th_img = Image.open(f"Assets/th_pics/town-hall-{th_level}{e_}.png")
                size = 60, 60
                th_img.thumbnail(size, Image.ANTIALIAS)
                spot += 1
                background.paste(th_img, (635 + (80 * spot), 662 + (106 * count)), th_img.convert("RGBA"))
                draw.text((635 + (80 * spot), 662 + (106 * count)), f"{th_count}", anchor="mm", fill=(255, 255, 255),
                          stroke_width=stroke, stroke_fill=(0, 0, 0), font=small_numbers)
                if spot >= 7:
                    break

            star_img = Image.open(f"ImageGen/league_badges/679_0.png")
            size = 45, 45
            star_img.thumbnail(size, Image.ANTIALIAS)
            # if 2 <=count < 7:

            background.paste(star_img, (1440, 665 + (106 * count)), star_img.convert("RGBA"))
            draw.text((1400, 685 + (107 * count)), f"{stars}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,
                      stroke_fill=(0, 0, 0), font=stat_numbers)
            draw.text((1647, 685 + (107 * count)), f"{int(destruction)}%", anchor="mm", fill=(255, 255, 255),
                      stroke_width=stroke, stroke_fill=(0, 0, 0), font=perc_numbers)

        league_name = f"War{base_clan.war_league.name.replace('League', '').replace(' ', '')}.png"
        league_img = Image.open(f"ImageGen/league_badges/{league_name}")
        size = 400, 400
        league_img = league_img.resize(size, Image.ANTIALIAS)
        background.paste(league_img, (785, 80), league_img.convert("RGBA"))

        draw.text((975, 520), f"{base_clan.war_league}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,
                  stroke_fill=(0, 0, 0), font=league_name_font)
        draw.text((515, 135), f"{len(cwl.rounds)}/{len(cwl.clans) - 1}", anchor="mm", fill=(255, 255, 255),
                  stroke_width=stroke, stroke_fill=(0, 0, 0), font=league_name_font)

        start = coc.utils.get_season_start().replace(tzinfo=pytz.utc).date()
        month = start.month
        if month == 12:
            month = 0
        month = calendar.month_name[month + 1]
        date_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 24)
        draw.text((387, 75), f"{month} {start.year}", anchor="mm", fill=(237, 191, 33), stroke_width=3,
                  stroke_fill=(0, 0, 0), font=date_font)

        def save_im(background):
            # background.show()
            temp = io.BytesIO()
            # background = background.resize((725, 471))
            # background = background.resize((1036, 673))
            background.save(temp, format="png", compress_level=1)
            temp.seek(0)
            file = disnake.File(fp=temp, filename="filename.png")
            temp.close()
            return file

        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(None, save_im, background)

        await ctx.send(file=file)


    @commands.slash_command(name="create_war_ids", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def create_war_ids(self, ctx: disnake.ApplicationCommandInteraction):
        things = []
        for war in await self.bot.clan_wars.find({}).to_list(length=100000):
            war_id = war.get("war_id")
            if war.get("custom_id") is not None:
                continue
            source = string.ascii_letters
            custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()

            is_used = await self.bot.clan_wars.find_one({"custom_id": custom_id})
            while is_used is not None:
                custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
                is_used = await self.bot.clan_wars.find_one({"custom_id": custom_id})

            things.append(UpdateOne({"war_id": war_id}, {"$set" : {"custom_id": custom_id}}))

        await self.bot.clan_wars.bulk_write(things)
        print("done")


    @testthis.autocomplete("clan")
    @raid_map.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=5)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[0:25]


def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))