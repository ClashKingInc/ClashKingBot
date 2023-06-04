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
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

from utils.constants import TOWNHALL_LEVELS

class ChatBot:
    def __init__(self, system=""):
        self.system = system
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.messages)
        # Uncomment this to print out token usage each time, e.g.
        # {"completion_tokens": 86, "prompt_tokens": 26, "total_tokens": 112}
        # print(completion.usage)
        return completion.choices[0].message.content



class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #self.bot.coc_client.add_events(self.member_attack)
        self.count = 0

    @commands.Cog.listener()
    async def on_connect(self):
        print("connected")


    @commands.slash_command(name="summary")
    async def summary(self, ctx: disnake.ApplicationCommandInteraction, num_messages: int = 100):
        await ctx.response.defer(ephemeral=True)
        channel: disnake.TextChannel = ctx.channel
        message_text = "Please summarize this conversation:\n"
        try:
            messages = await channel.history(limit=num_messages).flatten()
        except:
            messages = []
        if not messages:
            return await ctx.edit_original_message(content="I don't have permission to view this channel")
        for message in reversed(messages):
            if message.webhook_id is None and message.author.bot:
                continue
            if message.content == "":
                continue
            if len(message_text) + len(f"{message.author.display_name} said: {message.content}\n") > 4000:
                continue
            message_text += f"{message.author.display_name} said: {message.content}\n"
        magicbot = ChatBot(f"You are a chatbot that helps summarize conversations. Summarize using only bullet points. Use up to 25 bullet points.")
        message = magicbot(message_text)

        await ctx.edit_original_message(content=f"Summary of the last {num_messages} messages in {channel.name}:\n {message}")

    #@commands.command(name="example")
    @commands.command(name="example")
    async def example(self, ctx: disnake.ApplicationCommandInteraction):
        clan = await self.bot.getClan("#280U89YQR")
        embed = disnake.Embed(title=f"{clan.name} Week 5/23-5/30 Summary",
              description=f"`Trophies        `{self.bot.emoji.trophy}`{clan.points}  `{self.bot.emoji.up_green_arrow}`+500  `{self.bot.emoji.globe}`#254 `{self.bot.emoji.discord}`#2`\n"
                          f"`Builder Trophies`{self.bot.emoji.trophy}`{clan.versus_points}  `{self.bot.emoji.up_green_arrow}`+25   `{self.bot.emoji.globe}`#3457`{self.bot.emoji.discord}`#1`\n"
                          f"`Donations       `{self.bot.emoji.clan_castle}`500,103`{self.bot.emoji.up_green_arrow}`+14265`{self.bot.emoji.globe}`#23  `{self.bot.emoji.discord}`#1`\n"
                          f"`TH Compo        `{self.bot.fetch_emoji(15)}`14.97  `{self.bot.emoji.up_green_arrow}`+0.5  `{self.bot.emoji.discord}`#2   `\n"
                          f"`War Stars       `{self.bot.emoji.war_star}`387    `{self.bot.emoji.up_green_arrow}`+23   `{self.bot.emoji.discord}`#8   `\n"
                          f"`Attack Wins     `{self.bot.emoji.thick_sword}`2,903  `{self.bot.emoji.up_green_arrow}`+492  `{self.bot.emoji.globe}`#201 `{self.bot.emoji.discord}`#4`\n"
                          f"`Activity        `{self.bot.emoji.clock}`5,607  `{self.bot.emoji.up_green_arrow}`+1003 `{self.bot.emoji.globe}`#1   `{self.bot.emoji.discord}`#1`\n"
                          f"`Wars Won        `{self.bot.emoji.war_star}`3      `{self.bot.emoji.up_green_arrow}`+0    `{self.bot.emoji.discord}`#1   `\n",
              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.url)
        await ctx.send(embed=embed)


    @commands.slash_command(name="hitrate")
    async def hitrate(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        text = ""
        pipeline = [
            {"$match": {"$and" : [{"type" : "clanCapitalContributions"}, {"clan" : "#2GYQ02JYP"}]}},
            {"$sort": {"time": 1}},
            {"$limit" : 50},
            {"$lookup": {"from": "player_stats", "localField": "tag", "foreignField": "tag", "as": "name"}},
            {"$set": {"name": "$name.name"}}
        ]
        results = await self.bot.player_history.aggregate(pipeline).to_list(length=None)
        missing = 0
        for result in results:
            if result.get("p_value") is None:
                missing += 1
                continue
            diff = result.get("value") - result.get("p_value", 0)
            name = result.get("name")[0]
            text += f"<t:{result.get('time')}:R> {diff} {name}\n"
        print(missing)
        embed = disnake.Embed(description=text)
        await ctx.send(embed=embed)

    @commands.slash_command(name="owner_anniversary", guild_ids=[923764211845312533])
    @commands.is_owner()
    async def anniversary(self, ctx: disnake.ApplicationCommandInteraction):
        guild = ctx.guild
        await ctx.send(content="Edited 0 members")
        x = 0
        twelve_month = disnake.utils.get(ctx.guild.roles, id=1029249316981833748)
        nine_month = disnake.utils.get(ctx.guild.roles, id=1029249365858062366)
        six_month = disnake.utils.get(ctx.guild.roles, id=1029249360178987018)
        three_month = disnake.utils.get(ctx.guild.roles, id=1029249480261906463)
        for member in guild.members:
            if member.bot:
                continue
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
        await ctx.edit_original_message(content="Done")


    @commands.command(name='leave')
    @commands.is_owner()
    async def leaveg(self,ctx, *, guild_name):
        guild = disnake.utils.get(self.bot.guilds, name=guild_name)  # Get the guild by name
        if guild is None:
            await ctx.send("No guild with that name found.")  # No guild found
            return
        await guild.leave()  # Guild found
        await ctx.send(f"I left: {guild.name}!")


    '''@commands.slash_command(name="raid", description="Image showing the current raid map")'''
    '''@coc.ClientEvents.raid_loop_start()
    async def raid_loop(self, iter_spot):
        print(iter_spot)'''


    @coc.RaidEvents.new_offensive_opponent()
    async def new_opponent(self, clan: coc.RaidClan, raid: RaidLogEntry):
        channel = await self.bot.getch_channel(1071566470137511966)
        district_text = ""
        for district in clan.districts:
            name = "District"
            if district.id == 70000000:
                name = "Capital"
            name = f"{name}_Hall{district.hall_level}"
            district_emoji = self.bot.fetch_emoji(name=name)
            district_text += f"{district_emoji}`Level {district.hall_level:<2}` - {district.name}\n"
        detailed_clan = await self.bot.getClan(clan.tag)
        embed = disnake.Embed(title=f"**New Opponent : {clan.name}**",
                             description=f"Raid Clan # {len(raid.attack_log)}\n"
                                         f"Location: {detailed_clan.location.name}\n"
                                         f"Get their own raid details & put some averages here",
                             color=disnake.Color.green())
        embed.add_field(name="Districts", value=district_text)
        embed.set_thumbnail(url=clan.badge.url)
        await channel.send(embed=embed)

    @coc.RaidEvents.raid_attack()
    async def member_attack(self, old_member: coc.RaidMember, member: coc.RaidMember, raid: RaidLogEntry):
        channel = await self.bot.getch_channel(1071566470137511966)
        previous_loot = old_member.capital_resources_looted if old_member is not None else 0
        looted_amount = member.capital_resources_looted - previous_loot
        if looted_amount == 0:
            return
        embed = disnake.Embed(
            description=f"[**{member.name}**]({member.share_link}) raided {self.bot.emoji.capital_gold}{looted_amount} | {self.bot.emoji.thick_sword} Attack #{member.attack_count}/{member.attack_limit + member.bonus_attack_limit}\n"
            , color=disnake.Color.green())
        clan_name = await self.bot.clan_db.find_one({"tag": raid.clan_tag})
        embed.set_author(name=f"{clan_name['name']}")
        off_medal_reward = calc_raid_medals(raid.attack_log)
        embed.set_footer(text=f"{numerize.numerize(raid.total_loot, 2)} Total CG | Calc Medals: {off_medal_reward}")
        await channel.send(embed=embed)


    @coc.RaidEvents.defense_district_destruction_change()
    async def district_destruction(self, previous_district: coc.RaidDistrict, district: coc.RaidDistrict):
        if self.count >= 20:
            return
        self.count += 1
        channel = await self.bot.getch_channel(1071566470137511966)
        #print(district.destruction)
        name = "District"
        if district.id == 70000000:
            name = "Capital"
        name = f"{name}_Hall{district.hall_level}"
        district_emoji = self.bot.fetch_emoji(name=name).partial_emoji
        color = disnake.Color.yellow()
        if district.destruction == 100:
            color = disnake.Color.red()

        if previous_district is None:
            previous_destr = 0
            previous_gold = 0
        else:
            previous_destr = previous_district.destruction
            previous_gold = previous_district.looted

        added = ""
        cg_added = ""
        if district.destruction-previous_destr != 0:
            added = f" (+{district.destruction-previous_destr}%)"
            cg_added = f" (+{district.looted-previous_gold})"

        embed = disnake.Embed(description=f"{self.bot.emoji.thick_sword}{district.destruction}%{added} | {self.bot.emoji.capital_gold}{district.looted}{cg_added} | Atk #{district.attack_count}\n"
                                          , color=color)
        clan_name = await self.bot.clan_db.find_one({"tag" : district.raid_clan.raid_log_entry.clan_tag})
        embed.set_author(icon_url=district_emoji.url, name=f"{district.name} Defense | {clan_name['name']}")
        embed.set_footer(icon_url=district.raid_clan.badge.url,
                         text=f"{district.raid_clan.name} | {district.raid_clan.destroyed_district_count}/{len(district.raid_clan.districts)} Districts Destroyed")
        await channel.send(embed=embed)


    @commands.slash_command(name="see-listeners")
    async def listen(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.send(self.bot.coc_client._listeners["raid"])

    @commands.slash_command(name="raid-map", description="See the live raid map")
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

    def leagueAndTrophies(self, league):

        if (league == "Bronze League III"):
            emoji = "<:BronzeLeagueIII:601611929311510528>"
        elif (league == "Bronze League II"):
            emoji = "<:BronzeLeagueII:601611942850986014>"
        elif (league == "Bronze League I"):
            emoji = "<:BronzeLeagueI:601611950228635648>"
        elif (league == "Silver League III"):
            emoji = "<:SilverLeagueIII:601611958067920906>"
        elif (league == "Silver League II"):
            emoji = "<:SilverLeagueII:601611965550428160>"
        elif (league == "Silver League I"):
            emoji = "<:SilverLeagueI:601611974849331222>"
        elif (league == "Gold League III"):
            emoji = "<:GoldLeagueIII:601611988992262144>"
        elif (league == "Gold League II"):
            emoji = "<:GoldLeagueII:601611996290613249>"
        elif (league == "Gold League I"):
            emoji = "<:GoldLeagueI:601612010492526592>"
        elif (league == "Crystal League III"):
            emoji = "<:CrystalLeagueIII:601612021472952330>"
        elif (league == "Crystal League II"):
            emoji = "<:CrystalLeagueII:601612033976434698>"
        elif (league == "Crystal League I"):
            emoji = "<:CrystalLeagueI:601612045359775746>"
        elif (league == "Master League III"):
            emoji = "<:MasterLeagueIII:601612064913621002>"
        elif (league == "Master League II"):
            emoji = "<:MasterLeagueII:601612075474616399>"
        elif (league == "Master League I"):
            emoji = "<:MasterLeagueI:601612085327036436>"
        elif (league == "Champion League III"):
            emoji = "<:ChampionLeagueIII:601612099226959892>"
        elif (league == "Champion League II"):
            emoji = "<:ChampionLeagueII:601612113345249290>"
        elif (league == "Champion League I"):
            emoji = "<:ChampionLeagueI:601612124447440912>"
        elif (league == "Titan League III"):
            emoji = "<:TitanLeagueIII:601612137491726374>"
        elif (league == "Titan League II"):
            emoji = "<:TitanLeagueII:601612148325744640>"
        elif (league == "Titan League I"):
            emoji = "<:TitanLeagueI:601612159327141888>"
        elif (league == "Legend League"):
            emoji = "<:LegendLeague:601612163169255436>"
        else:
            emoji = "<:Unranked:601618883853680653>"

        return emoji

    async def cwl_ranking_create(self, clan: coc.Clan):
        try:
            group = await self.bot.coc_client.get_league_group(clan.tag)
            state = group.state
            if str(state) == "preparation" and len(group.rounds) == 1:
                return {clan.tag: None}
            if str(group.season) != self.bot.gen_season_date():
                return {clan.tag: None}
        except:
            return {clan.tag: None}

        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_name = defaultdict(str)

        rounds = group.rounds
        for round in rounds:
            for war_tag in round:
                war = await self.bot.coc_client.get_league_war(war_tag)
                if str(war.status) == "won":
                    star_dict[war.clan.tag] += 10
                elif str(war.status) == "lost":
                    star_dict[war.opponent.tag] += 10
                tag_to_name[war.clan.tag] = war.clan.name
                tag_to_name[war.opponent.tag] = war.opponent.name
                for player in war.members:
                    attacks = player.attacks
                    for attack in attacks:
                        star_dict[player.clan.tag] += attack.stars
                        dest_dict[player.clan.tag] += attack.destruction

        star_list = []
        for tag, stars in star_dict.items():
            destruction = dest_dict[tag]
            name = tag_to_name[tag]
            star_list.append([tag, stars, destruction])

        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
        place= 1
        for item in sorted_list:
            war_leagues = open(f"Assets/war_leagues.json")
            war_leagues = json.load(war_leagues)
            promo = [x["promo"] for x in war_leagues["items"] if x["name"] == clan.war_league.name][0]
            demo = [x["demote"] for x in war_leagues["items"] if x["name"] == clan.war_league.name][0]
            if place <= promo:
                emoji = "<:warwon:932212939899949176>"
            elif place >= demo:
                emoji = "<:warlost:932212154164183081>"
            else:
                emoji = "<:dash:933150462818021437>"
            tag = item[0]
            stars = str(item[1])
            dest = str(item[2])
            if place == 1:
                rank = f"{place}st"
            elif place == 2:
                rank = f"{place}nd"
            elif place == 3:
                rank = f"{place}rd"
            else:
                rank = f"{place}th"
            if tag == clan.tag:
                tier = str(clan.war_league.name).count("I")
                return {clan.tag : f"{emoji}`{rank}` {self.leagueAndTrophies(clan.war_league.name)}{SUPER_SCRIPTS[tier]}"}
            place += 1

    @commands.slash_command(name="get_lb")
    @commands.is_owner()
    async def get_lb(self, ctx: disnake.ApplicationCommandInteraction):
        r = await self.bot.link_client.get_link("UC22UUU8")
        print(r)
        return r
        dates = await self.bot.coc_client.get_seasons(29000022)
        dates.append(self.bot.gen_season_date())
        dates = reversed(dates)
        for season in dates:
            #await self.bot.player_stats.create_index([(f"donations.{season}.donated", 1)], background=True)
            #await self.bot.player_stats.create_index([(f"donations.{season}.received", 1)], background=True)
            pass



    @commands.slash_command(name="html")
    @commands.is_owner()
    async def html(self, ctx: disnake.ApplicationCommandInteraction):
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

    @commands.slash_command(name="cwl-image", description="Image showing cwl rankings & th comps")
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
                background.paste(badge, (200, 645 + (105* count)), badge.convert("RGBA"))
            if clan.tag == base_clan.tag:
                color = (136,193,229)
            else:
                color = (255, 255, 255)
            draw.text((315, 690 + (106 * count)), f"{clan.name[:17]}", anchor="lm", fill=color,stroke_width=stroke, stroke_fill=(0, 0, 0), font=clan_name)
            promo = [x["promo"] for x in war_leagues["items"] if x["name"] == base_clan.war_league.name][0]
            demo = [x["demote"] for x in war_leagues["items"] if x["name"] == base_clan.war_league.name][0]
            extra = 0
            if count + 1 <= promo:
                placement_img = Image.open("ImageGen/league_badges/2168_0.png")
                color = (166,217,112)
            elif count + 1 >= demo:
                placement_img = Image.open("ImageGen/league_badges/2170_0.png")
                color = (232,16,17)
            else:
                placement_img = Image.open("ImageGen/league_badges/2169_0.png")
                extra = 15
                color = (255, 255, 255)

            draw.text((100, 690 + (106 * count)), f"{count + 1}.", anchor="lm", fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0), font=numbers)
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
                draw.text((635 + (80 * spot), 662 + (106 * count)), f"{th_count}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,stroke_fill=(0, 0, 0), font=small_numbers)
                if spot >= 7:
                    break

            star_img = Image.open(f"ImageGen/league_badges/679_0.png")
            size = 45, 45
            star_img.thumbnail(size, Image.ANTIALIAS)
            #if 2 <=count < 7:

            background.paste(star_img, (1440, 665 + (106 * count)), star_img.convert("RGBA"))
            draw.text((1400, 685 + (107 * count)), f"{stars}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0), font=stat_numbers)
            draw.text((1647, 685 + (107 * count)), f"{int(destruction)}%", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,stroke_fill=(0, 0, 0), font=perc_numbers)


        league_name = f"War{base_clan.war_league.name.replace('League','').replace(' ','')}.png"
        league_img = Image.open(f"ImageGen/league_badges/{league_name}")
        size = 400, 400
        league_img = league_img.resize(size, Image.ANTIALIAS)
        background.paste(league_img, (785, 80), league_img.convert("RGBA"))

        draw.text((975, 520), f"{base_clan.war_league}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,stroke_fill=(0, 0, 0), font=league_name_font)
        draw.text((515, 135), f"{len(cwl.rounds)}/{len(cwl.clans) - 1}", anchor="mm", fill=(255, 255, 255), stroke_width=stroke,stroke_fill=(0, 0, 0), font=league_name_font)

        start = coc.utils.get_season_start().replace(tzinfo=pytz.utc).date()
        month = start.month
        if month == 12:
            month = 0
        month = calendar.month_name[month + 1]
        date_font = ImageFont.truetype("ImageGen/SCmagic.ttf", 24)
        draw.text((387, 75), f"{month} {start.year}", anchor="mm", fill=(237,191,33), stroke_width=3, stroke_fill=(0, 0, 0), font=date_font)

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

    @commands.slash_command(name="test_fw")
    async def testfwlog(self, ctx: disnake.ApplicationCommandInteraction):
        w = await self.bot.war_client.war_result(clan_tag="UCR0Y2G")
        print(w)







def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))