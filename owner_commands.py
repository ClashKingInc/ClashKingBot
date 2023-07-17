import json

import disnake
from disnake.ext import commands
clan_tags = ["#2P0JJQGUJ"]
known_streak = []
count = 0
list_size = 0
from CustomClasses.CustomBot import CustomClient

war_leagues = json.load(open(f"Assets/war_leagues.json"))

leagues = ["Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]
import os
import coc
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry

from Link_and_Eval.eval_logic import eval_logic
from CustomClasses.ReminderClass import Reminder
from utils.ClanCapital import get_raidlog_entry, gen_raid_weekend_datestrings
from BoardCommands.Utils.Clan import clan_raid_weekend_raid_stats, clan_raid_weekend_donation_stats
from ImageGen.ClanCapitalResult import generate_raid_result_image, calc_raid_medals
from pymongo import UpdateOne
from coc.raid import RaidLogEntry, RaidAttack
from numerize import numerize
from CustomClasses.CustomServer import DatabaseClan
from utils.discord_utils import get_webhook_for_channel
from Exceptions.CustomExceptions import MissingWebhookPerms
from datetime import datetime
from pytz import utc


class OwnerCommands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot
        #self.bot.coc_client.add_events(self.member_attack)
        self.count = 0


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

    @commands.slash_command(name="go", guild_ids=[412991112161001472])
    @commands.is_owner()
    async def test(self, ctx: disnake.ApplicationCommandInteraction):
        bot = self.bot
        pipeline = [
            {"$match": {"type": "roster"}},
            {"$lookup": {"from": "rosters", "localField": "roster", "foreignField": "_id", "as": "roster"}},
            {"$set": {"roster": {"$first": "$roster"}}}
        ]
        for reminder in await bot.reminders.aggregate(pipeline=pipeline).to_list(length=None):
            reminder = Reminder(bot=bot, data=reminder)
            if reminder.server_id not in [412991112161001472]:
                continue
            if not reminder.roster.is_valid or reminder.time is None or len(reminder.roster.players) == 0:
                continue

            try:
                channel = await bot.getch_channel(reminder.channel_id)
            except (disnake.NotFound, disnake.Forbidden):
                await reminder.delete()
                continue

            server = await bot.getch_guild(reminder.server_id)
            if server is None:
                continue

            time = reminder.time.replace(" hr", "")
            seconds_before_to_ping = int(float(time) * 3600)

            max_diff = 2 * 60  # time in seconds between runs
            now = datetime.now(tz=utc)
            roster_time = datetime.fromtimestamp(float(reminder.roster.time), tz=utc)
            time_until_time = (roster_time - now).total_seconds()
            # goes negative if now >= time
            # gets smaller as we get closer

            # we want to ping when we are closer to the time than further, so when seconds_before
            # larger - smaller >= 0
            # smaller - larger <= 0
            if seconds_before_to_ping - time_until_time >= 0 and seconds_before_to_ping - time_until_time <= max_diff:
                members = []
                if reminder.ping_type == "All Roster Members":
                    members = reminder.roster.players
                elif reminder.ping_type == "Not in Clan":
                    members = await reminder.roster.missing_list(reverse=False)
                elif reminder.ping_type == "Subs Only":
                    members = [p for p in reminder.roster.players if p.get("sub", False)]

                if not members:
                    continue
                links = await bot.link_client.get_links(*[p.get("tag") for p in members])
                missing_text_list = []
                text = ""
                for player_tag, discord_id in links:
                    name = next((player for player in members if player.get("tag") == player_tag), {})
                    name = name.get("name")
                    member = await server.getch_member(discord_id)
                    if len(text) + len(reminder.custom_text) + 100 >= 2000:
                        missing_text_list.append(text)
                        text = ""
                    if member is None:
                        text += f"{name} | {player_tag}\n"
                    else:
                        text += f"{name} | {member.mention}\n"

                if text != "":
                    missing_text_list.append(text)
                badge = await bot.create_new_badge_emoji(url=reminder.roster.clan_badge)
                for text in missing_text_list:
                    reminder_text = f"**{badge}{reminder.roster.clan_name} | {reminder.roster.alias} | {bot.timestamper(reminder.roster.time).relative}**\n\n" \
                                    f"{text}"
                    buttons = []
                    if text == missing_text_list[-1]:
                        reminder_text += f"\n{reminder.custom_text}"
                        button = disnake.ui.Button(label="Clan Link", emoji="🔗", style=disnake.ButtonStyle.url,
                                                   url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag=%23{reminder.roster.roster_result.get('clan_tag').strip('#')}")
                        buttons = [disnake.ui.ActionRow(button)]
                    try:
                        await channel.send(content=reminder_text, components=buttons)
                    except:
                        pass

    @commands.slash_command(name="restart-customs", guild_ids=[1103679645439754335])
    @commands.is_owner()
    async def restart_custom(self, ctx: disnake.ApplicationCommandInteraction, top: int):
        for x in range(4, top+1):
            os.system(f"pm2 restart {x}")



    @commands.slash_command(name="migrate", guild_ids=[1103679645439754335])
    @commands.is_owner()
    async def migrate(self, ctx: disnake.ApplicationCommandInteraction):

        cursor = self.bot.welcome.find({})
        all_them = await cursor.to_list(length=None)
        print(len(all_them))
        for document in all_them:
            api_token = document.get("api_token", True)
            await self.bot.server_db.update_one({"server" : document.get("server")}, {"$set" : {"api_token" : api_token}})


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


    '''@commands.slash_command(name="owner_anniversary", guild_ids=[923764211845312533])
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
        print("done")'''


    '''@testthis.autocomplete("clan")
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
        return clan_list[0:25]'''


def setup(bot: CustomClient):
    bot.add_cog(OwnerCommands(bot))