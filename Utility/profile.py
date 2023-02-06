import coc
import disnake
from coc.raid import RaidLogEntry
from datetime import date, timedelta, datetime
from disnake.ext import commands
from Utility.profile_embeds import *
from Assets.emojiDictionary import emojiDictionary
from Utility.pagination import button_pagination
from utils.search import search_results
from utils.ClanCapital import gen_raid_weekend_datestrings, get_raidlog_entry
from utils.troop_methods import heros, heroPets
from Assets.thPicDictionary import thDictionary
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from typing import List
import pytz
utc = pytz.utc
from DiscordLevelingCard import RankCard, Settings
from operator import attrgetter
import asyncio
from utils.discord_utils import interaction_handler
import calendar
from collections import defaultdict
import operator
from coc.raid import RaidMember, RaidLogEntry

LEVELS_AND_XP = {
    '0': 0,
    '1': 100,
    '2': 255,
    '3': 475,
    '4': 770,
    '5': 1150,
    '6': 1625,
    '7': 2205,
    '8': 2900,
    '9': 3720,
    '10': 4675,
    '11': 5775,
    '12': 7030,
    '13': 8450,
    '14': 10045,
    '15': 11825,
    '16': 13800,
    '17': 15980,
    '18': 18375,
    '19': 20995,
    '20': 23850,
    '21': 26950,
    '22': 30305,
    '23': 33925,
    '24': 37820,
    '25': 42000,
    '26': 46475,
    '27': 51255,
    '28': 56350,
    '29': 61770,
    '30': 67525,
    '31': 73625,
    '32': 80080,
    '33': 86900,
    '34': 94095,
    '35': 101675,
    '36': 109650,
    '37': 118030,
    '38': 126825,
    '39': 136045,
    '40': 145700,
    '41': 155800,
    '42': 166355,
    '43': 177375,
    '44': 188870,
    '45': 200850,
    '46': 213325,
    '47': 226305,
    '48': 239800,
    '49': 253820,
    '50': 268375,
    '51': 283475,
    '52': 299130,
    '53': 315350,
    '54': 332145,
    '55': 349525,
    '56': 367500,
    '57': 386080,
    '58': 405275,
    '59': 425095,
    '60': 445550,
    '61': 466650,
    '62': 488405,
    '63': 510825,
    '64': 533920,
    '65': 557700,
    '66': 582175,
    '67': 607355,
    '68': 633250,
    '69': 659870,
    '70': 687225,
    '71': 715325,
    '72': 744180,
    '73': 773800,
    '74': 804195,
    '75': 835375,
    '76': 867350,
    '77': 900130,
    '78': 933725,
    '79': 968145,
    '80': 1003400,
    '81': 1039500,
    '82': 1076455,
    '83': 1114275,
    '84': 1152970,
    '85': 1192550,
    '86': 1233025,
    '87': 1274405,
    '88': 1316700,
    '89': 1359920,
    '90': 1404075,
    '91': 1449175,
    '92': 1495230,
    '93': 1542250,
    '94': 1590245,
    '95': 1639225,
    '96': 1689200,
    '97': 1740180,
    '98': 1792175,
    '99': 1845195,
    '100': 1899250
}

class profiles(commands.Cog, name="Profile"):

    def __init__(self, bot: CustomClient):
        self.bot = bot
    @commands.slash_command(name="player")
    async def player(self, ctx):
        pass

    @player.sub_command(name="lookup", description="Lookup players or discord users")
    async def lookup(self, ctx: disnake.ApplicationCommandInteraction, tag: str=None, discord_user:disnake.Member=None):
        """
            Parameters
            ----------
            tag: (optional) tag to lookup
            discord_user: (optional) discord user to lookup
        """
        search_query = None
        if tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif tag is not None:
            search_query = tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(self.bot, search_query)
        results = results[:25]
        if results == []:
            return await ctx.edit_original_message(content="No results were found.", embed=None)
        msg = await ctx.original_message()

        await button_pagination(self.bot, ctx, msg, results)


    @player.sub_command(name="account-list", description="List of accounts a user has & average th compo")
    async def list(self, ctx: disnake.ApplicationCommandInteraction, discord_user:disnake.Member=None):
        if discord_user is None:
            search_query = str(ctx.author.id)
        else:
            search_query = str(discord_user.id)
        await ctx.response.defer()

        results = await search_results(self.bot, search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.")

        text = ""
        total = 0
        sumth = 0
        embeds = []
        for player in results:
            emoji = emojiDictionary(player.town_hall)
            th = player.town_hall
            sumth += th
            total += 1
            text += f"{emoji} {player.name}\n"

        average = round((sumth / total), 2)
        embed = disnake.Embed(
            description=text,
            color=disnake.Color.green())

        embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
        await ctx.edit_original_message(embed=embed)


    @player.sub_command(name="invite", description="Embed with basic info & link for a player to be invited")
    async def invite(self, ctx: disnake.ApplicationCommandInteraction, player_tag):
        await ctx.response.defer()
        player = await self.bot.getPlayer(player_tag)
        if player is None:
            return await ctx.send("Not a valid playerTag.")

        try:
            clan = player.clan.name
            clan = f"{clan}"
        except:
            clan = "None"
        hero = heros(bot=self.bot, player=player)
        pets = heroPets(bot=self.bot, player=player)
        if hero is None:
            hero = ""
        else:
            hero = f"**Heroes:**\n{hero}\n"

        if pets is None:
            pets = ""
        else:
            pets = f"**Pets:**\n{pets}\n"

        embed = disnake.Embed(title=f"**Invite {player.name} to your clan:**",
                              description=f"{player.name} - TH{player.town_hall}\n" +
                                          f"Tag: {player.tag}\n" +
                                          f"Clan: {clan}\n" +
                                          f"Trophies: {player.trophies}\n"
                                          f"War Stars: {player.war_stars}\n"
                                          f"{hero}{pets}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=thDictionary(player.town_hall))

        stat_buttons = [
            disnake.ui.Button(label=f"Open In-Game",
                              url=player.share_link),
            disnake.ui.Button(label=f"Clash of Stats",
                              url=f"https://www.clashofstats.com/players/{player.tag.strip('#')}/summary"),
            disnake.ui.Button(label=f"Clash Ninja",
                              url=f"https://www.clash.ninja/stats-tracker/player/{player.tag.strip('#')}")]
        buttons = disnake.ui.ActionRow()
        for button in stat_buttons:
            buttons.append_item(button)

        await ctx.send(embed=embed, components=[buttons])

    @player.sub_command(name="upgrades", description="Show upgrades needed for an account")
    async def upgrades(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str=None, discord_user:disnake.Member=None):
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(self.bot, search_query)
        embed = upgrade_embed(self.bot, results[0])
        components = []
        if len(results) > 1:
            player_results = []
            for count, player in enumerate(results):
                player_results.append(
                    disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                         value=f"{count}"))
            profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)
            st2 = disnake.ui.ActionRow()
            st2.append_item(profile_select)
            components = [st2]
        await ctx.send(embeds=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                     timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break

            await res.response.defer()
            current_page = int(res.values[0])
            embed = upgrade_embed(self.bot, results[current_page])
            await res.edit_original_message(embeds=embed)

    @player.sub_command(name="war-stats", description="War stats of a player or discord user")
    async def war_stats_player(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str=None, discord_user:disnake.Member=None, start_date = 0, end_date = 9999999999):
        """
            Parameters
            ----------
            player_tag: (optional) player to view war stats on
            discord_user: (optional) discord user's accounts to view war stats of
            start_date: (optional) filter stats by date, default is to view this season
            end_date: (optional) filter stats by date, default is to view this season
        """
        await ctx.response.defer()
        if start_date != 0 and end_date != 9999999999:
            start_date = int(datetime.strptime(start_date, "%d %B %Y").timestamp())
            end_date = int(datetime.strptime(end_date, "%d %B %Y").timestamp())
        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        players = await search_results(self.bot, search_query)
        if players == []:
            embed = disnake.Embed(description="**No matching player/discord user found**", colour=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.create_player_hr(player=players[0], start_date=start_date, end_date=end_date)
        await ctx.edit_original_message(embed=embed, components=self.player_components(players))
        if len(players) == 1:
            return
        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check, timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            page = int(res.values[0])
            embed = await self.create_player_hr(player=players[page], start_date=start_date, end_date=end_date)
            await res.edit_original_message(embed=embed)

    @commands.slash_command(name="game-rank", description="Get xp rank for in game activities")
    async def game_rank(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member = None):
        await ctx.response.defer()
        if member is None:
            self.author = ctx.author
            member = self.author

        custom = await self.bot.level_cards.find_one({"user_id" : ctx.author.id})
        if custom is not None:
            background_color = custom.get("background_color") if custom.get("background_color") is not None else "#36393f"
            background = custom.get("background_image") if custom.get("background_image") is not None else "https://media.discordapp.net/attachments/923767060977303552/1067289914443583488/bgonly1.jpg"
            text_color = custom.get("text_color") if custom.get("text_color") is not None else "white"
            bar_color = custom.get("bar_color") if custom.get("bar_color") is not None else "#b5cf3d"
        else:
            background_color = "#36393f"
            background = "https://media.discordapp.net/attachments/923767060977303552/1067289914443583488/bgonly1.jpg"
            text_color = "white"
            bar_color = "#b5cf3d"

        card_settings = Settings(
            background_color=background_color,
            background=background,
            text_color=text_color,
            bar_color=bar_color
        )

        linked_accounts: List[MyCustomPlayer] = await search_results(self.bot, str(member.id))
        if linked_accounts == []:
            await ctx.send(content="No Linked Acccounts")

        top_account = max(linked_accounts, key=attrgetter('level_points'))
        print(f"{top_account.name} | {top_account.tag}")
        level = int(max(self._find_level(current_total_xp=top_account.level_points), 0))
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        results = await self.bot.player_stats.find({"clan_tag": {"$in": clan_tags}}).sort("points", -1).to_list(1500)
        rank = None
        for r, result in enumerate(results, 1):
            if result.get("tag") == top_account.tag:
                rank = r
                break

        rank_card = RankCard(
                settings=card_settings,
                avatar=member.display_avatar.url,
                level=level,
                current_exp=top_account.level_points,
                max_exp=LEVELS_AND_XP[str(level+ 1)],
                username=f"{member}", account=top_account.name[:13],
                rank = rank
            )
        image = await rank_card.card3()
        await ctx.edit_original_message(file=disnake.File(image, filename="rank.png"))

    @player.sub_command(name="stats", description="Get stats for different areas of a player")
    async def player_stats(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member, type:str =commands.Param(choices=["CWL", "Raids"])):
        if type == "Raids":
            return await self.raid_stalk(ctx=ctx, member=member)
        else:
            return await self.cwl_stalk(ctx=ctx, member=member)

    async def cwl_stalk(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
        await ctx.response.defer()
        tags = await self.bot.link_client.get_linked_players(discord_id=member.id)
        if not tags:
            return await ctx.send("No players linked.")
        # players = await self.bot.get_players(tags=tags)
        first_of_month = int(datetime.now().replace(day=1, hour=1).timestamp())
        true_month = datetime.now().month
        month = calendar.month_name[true_month]

        townhalls_attacked = []
        my_townhalls = []
        hits = defaultdict(list)
        percents = defaultdict(list)
        embeds = []
        townhalls_defended = []
        defense_hits = defaultdict(list)
        defense_percents = defaultdict(list)

        for player in tags:
            results = await self.bot.warhits.find({"$and": [
                {"tag": player},
                {"war_type": "cwl"},
                {"_time": {"$gte": first_of_month}}
            ]}).sort("_time", 1).to_list(length=10)
            text = ""
            if not results:
                continue
            townhall = 1
            name = ""
            clan_tag = ""
            for day, result in enumerate(results, 1):
                hits[f"{result['townhall']}v{result['defender_townhall']}"].append(result['stars'])
                percents[f"{result['townhall']}v{result['defender_townhall']}"].append(result['destruction'])
                my_townhalls.append(result['townhall'])
                townhalls_attacked.append([result['defender_townhall']])
                star_str = ""
                stars = result['stars']
                for x in range(0, stars):
                    star_str += self.bot.emoji.war_star.emoji_string
                for x in range(0, 3 - stars):
                    star_str += self.bot.emoji.no_star.emoji_string
                text += f"`Day {day} `| {star_str}`{result['destruction']:3}%`{emojiDictionary(result['townhall'])}" \
                        f"{self.bot.get_number_emoji(color='blue', number=result['townhall'])} **►** " \
                        f"{emojiDictionary(result['defender_townhall'])}{self.bot.get_number_emoji(color='blue', number=result['defender_townhall'])}\n"
                townhall = result['townhall']
                name = result['name']
                clan_tag = result['clan']

            defense_text = ""
            defense_results = await self.bot.warhits.find({"$and": [
                {"defender_tag": player},
                {"war_type": "cwl"},
                {"_time": {"$gte": first_of_month}}
            ]}).sort("_time", 1).to_list(length=10)
            for day, result in enumerate(defense_results, 1):
                defense_hits[f"{result['defender_townhall']}v{result['townhall']}"].append(result['stars'])
                defense_percents[f"{result['defender_townhall']}v{result['townhall']}"].append(result['destruction'])
                townhalls_defended.append([result['defender_townhall']])
                star_str = ""
                stars = result['stars']
                for x in range(0, stars):
                    star_str += self.bot.emoji.war_star.emoji_string
                for x in range(0, 3 - stars):
                    star_str += self.bot.emoji.no_star.emoji_string
                defense_text += f"`Day {day} `| {star_str}`{result['destruction']:3}%`{emojiDictionary(result['townhall'])}" \
                                f"{self.bot.get_number_emoji(color='blue', number=result['townhall'])} **►** " \
                                f"{emojiDictionary(result['defender_townhall'])}{self.bot.get_number_emoji(color='blue', number=result['defender_townhall'])}\n"
            if defense_text == "":
                defense_text = "No Defenses Yet"

            others_in_same_clan = await self.bot.warhits.find({"$and": [
                {"clan": clan_tag},
                {"war_type": "cwl"},
                {"_time": {"$gte": first_of_month}}
            ]}).to_list(length=1000)
            star_dict = defaultdict(int)
            dest_dict = defaultdict(int)
            for result in others_in_same_clan:
                star_dict[result["tag"]] += result["stars"]
                dest_dict[result["tag"]] += result["destruction"]

            star_list = []
            for tag, stars in star_dict.items():
                star_list.append([tag, stars, dest_dict[tag]])
            sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)

            placement = 0
            for count, item in enumerate(sorted_list, 1):
                if item[0] == player:
                    placement = count
                    break

            clan = await self.bot.getClan(clan_tag=clan_tag)
            embed = disnake.Embed(title=f"{name} | {clan.name}", color=disnake.Color.green())
            embed.add_field(name="Attacks", value=text, inline=False)
            embed.add_field(name="Defenses", value=defense_text, inline=False)
            embed.set_footer(icon_url=clan.badge.url,
                             text=f"#{placement}/{len(sorted_list)} in CWL Group | {clan.war_league.name}")
            embeds.append(embed)

        last_30_days = await self.bot.warhits.find({"$and": [
            {"tag": {"$in": tags}},
            {"war_type": {"$in": ["cwl", "random"]}},
            {"_time": {"$gte": int((datetime.now() - timedelta(days=35)).timestamp())}}
        ]}).sort("_time", 1).to_list(length=1000)
        seconds = []
        for result in last_30_days:
            time = datetime.fromtimestamp(result['_time'])
            seconds.append((time.hour * 60 * 60) + (time.minute * 60) + (time.second))
        average_seconds = int(sum(seconds) / len(seconds))
        now = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        average_time = datetime.fromtimestamp(now + average_seconds)
        average_time = f"<t:{int(average_time.timestamp())}:t>"

        def average(item):
            return (round(sum(item) / len(item), 2))

        def sort_by_th(item: str):
            return int(item.split("v")[0])

        def sort_by_other_th(item: str):
            return int(item.split("v")[-1])

        sorted_hits = sorted(hits.items(), key=lambda x: (sort_by_th(x[0]), sort_by_other_th(x[0])), reverse=True)
        # sorted_hits = sorted(sorted_hits.items(), key=lambda item: item[1])
        sorted_hits = dict(sorted_hits)
        th_text = "THvTH";
        stars_text = "Stars";
        perc_text = "Perc%"
        hitrate_text = f"`{th_text:>5} {stars_text:>4}{perc_text:>6}`\n"
        for type, stars in sorted_hits.items():
            hitrate_text += f"`{type:>5} {average(stars):>4.2f} {average(percents[type]):>5.1f}%`\n"
        if not embeds:
            return await ctx.send(embed=disnake.Embed(description=f"No CWL Stats found for {member.display_name}",
                                                      color=disnake.Color.red()))
        main_embed = disnake.Embed(title=f"{member.display_name} CWL Stats | {month} {datetime.now().year}",
                                   description=f"Avg. Attacks Around: {average_time}\n"
                                               f"**Average Hitrates:**\n{hitrate_text}",
                                   color=disnake.Color.gold())

        buttons = []
        if len(embeds) > 4:
            buttons = [disnake.ui.ActionRow(
                disnake.ui.Button(label=f"Next {min(5, len(embeds[4:9]))} Accounts", style=disnake.ButtonStyle.grey,
                                  custom_id="more_accounts"))]

        start_page = -1
        end_page = 4
        await ctx.send(embeds=([main_embed] + embeds)[:5], components=buttons)
        if len(embeds) <= 4:
            return
        message = await ctx.original_message()
        while True:
            try:
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=message)
            except:
                return await message.edit(components=[])
            start_page += 5
            end_page += 5
            await message.edit(components=[])
            buttons = None
            if len(embeds[start_page + 5:end_page + 5]) >= 1:
                buttons = [disnake.ui.ActionRow(
                    disnake.ui.Button(label=f"Next {min(5, len(embeds[start_page + 5:end_page + 5]))} Accounts",
                                      style=disnake.ButtonStyle.grey, custom_id="more_accounts"))]
            message = await ctx.followup.send(embeds=embeds[start_page:end_page], components=buttons)

    async def raid_stalk(self, ctx: disnake.ApplicationCommandInteraction, member: disnake.Member):
        await ctx.response.defer()
        tags = await self.bot.link_client.get_linked_players(discord_id=member.id)
        # players = await self.bot.get_players(tags=tags)
        first_of_month = int(datetime.now().replace(day=1, hour=1).timestamp())
        true_month = datetime.now().month
        month = calendar.month_name[true_month]
        if not tags:
            return await ctx.send(content="No players linked.")
        embeds = []
        total_looted = 0
        total_medals = 0
        clans = []
        highest_looted = 0
        highest_medals = 0
        num_accounts = 0
        for player in tags:
            member_looted = 0
            member_medals = 0
            results = await self.bot.raid_weekend_db.find({"data.members.tag": player}).sort("data.startTime",
                                                                                             1).to_list(length=5)
            if not results:
                continue
            text = ""
            member = None
            num_accounts += 1
            for result in results:
                member_result = next((item for item in result["data"]["members"] if item['tag'] == player), None)
                member = RaidMember(client=self.bot.coc_client, data=member_result,
                                        raid_log_entry=RaidLogEntry(client=self.bot.coc_client, data=result["data"],
                                                                        clan_tag=result["clan_tag"]))
                member = member
                raid: RaidLogEntry = member.raid_log_entry
                text += f"{self.bot.emoji.capital_gold}`{member.capital_resources_looted:5} | `{self.bot.emoji.thick_sword}`{member.attack_count:1} " \
                        f"| `{self.bot.emoji.raid_medal}`{(raid.offensive_reward * member.attack_count) + raid.defensive_reward:4} | {raid.end_time.time.strftime('%m-%d')}`\n"
                total_looted += member.capital_resources_looted
                if member.capital_resources_looted > highest_looted:
                    highest_looted = member.capital_resources_looted
                member_looted += member.capital_resources_looted
                total_medals += (raid.offensive_reward * member.attack_count) + raid.defensive_reward

                if (raid.offensive_reward * member.attack_count) + raid.defensive_reward > highest_medals:
                    highest_medals = (raid.offensive_reward * member.attack_count) + raid.defensive_reward
                member_medals += (raid.offensive_reward * member.attack_count) + raid.defensive_reward
                clans.append(raid.clan_tag)

            text = f"**Totals: {self.bot.emoji.capital_gold}{'{:,}'.format(member_looted)} | {self.bot.emoji.raid_medal}{member_medals}**\n{text}"
            embed = disnake.Embed(title=f"{member.name} Raid Performance", description=text,
                                  color=disnake.Color.green())
            embeds.append(embed)

        if not embeds:
            return await ctx.send("No Clan Capital Stats Found")
        main_embed = disnake.Embed(title=f"{ctx.author.display_name} Raid Stats | (last 8 weeks)",
                                   description=f"*Raided from {len(set(clans))} different clans w/ {num_accounts} accounts*\n"
                                               f"**Highest Medals:** {self.bot.emoji.raid_medal}{highest_medals}\n"
                                               f"**Highest Looted:** {self.bot.emoji.capital_gold}{'{:,}'.format(highest_looted)}\n"
                                               f"**Totals:** {self.bot.emoji.capital_gold}{'{:,}'.format(total_looted)} | {self.bot.emoji.raid_medal}{'{:,}'.format(total_medals)}",
                                   color=disnake.Color.gold())
        buttons = []
        if len(embeds) > 4:
            buttons = [disnake.ui.ActionRow(
                disnake.ui.Button(label=f"Next {min(5, len(embeds[4:9]))} Accounts", style=disnake.ButtonStyle.grey,
                                  custom_id="more_accounts"))]

        start_page = -1
        end_page = 4
        await ctx.send(embeds=([main_embed] + embeds)[:5], components=buttons)
        if len(embeds) <= 4:
            return
        message = await ctx.original_message()
        while True:
            try:
                res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, msg=message)
            except:
                return await message.edit(components=[])
            start_page += 5
            end_page += 5
            await message.edit(components=[])
            buttons = None
            if len(embeds[start_page + 5:end_page + 5]) >= 1:
                buttons = [disnake.ui.ActionRow(
                    disnake.ui.Button(label=f"Next {min(5, len(embeds[start_page + 5:end_page + 5]))} Accounts",
                                      style=disnake.ButtonStyle.grey, custom_id="more_accounts"))]
            message = await ctx.followup.send(embeds=embeds[start_page:end_page], components=buttons)


    def _find_level(self, current_total_xp: int):
        # check if the current xp matches the xp_needed exactly
        if current_total_xp in LEVELS_AND_XP.values():
            for level, xp_needed in LEVELS_AND_XP.items():
                if current_total_xp == xp_needed:
                    return int(level)
        else:
            for level, xp_needed in LEVELS_AND_XP.items():
                if 0 <= current_total_xp <= xp_needed:
                    level = int(level)
                    level -= 1
                    if level < 0:
                        level = 0
                    return level


    @player.sub_command(name="to-do", description="Get a list of things to be done (war attack, legends hits, capital raids etc)")
    async def to_do(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member=None):
        await ctx.response.defer()
        if discord_user is None:
            discord_user = ctx.author
        linked_accounts = await search_results(self.bot, str(discord_user.id))
        embed = await self.to_do_embed(discord_user=discord_user, linked_accounts=linked_accounts)
        await ctx.edit_original_message(embed=embed)

    async def to_do_embed(self, discord_user, linked_accounts):
        embed = disnake.Embed(title=f"{discord_user.display_name} To-Do List", color=disnake.Color.green())

        if linked_accounts == []:
            embed.description = "No accounts linked, use `/link` to get started!"
            return embed

        war_hits_to_do = await self.get_war_hits(linked_accounts=linked_accounts)
        if war_hits_to_do != "":
            embed.add_field(name="War Hits", value=war_hits_to_do, inline=False)

        legend_hits_to_do = await self.get_legend_hits(linked_accounts=linked_accounts)
        if legend_hits_to_do != "":
            embed.add_field(name="Legend Hits", value=legend_hits_to_do, inline=False)

        raid_hits_to_do = await self.get_raid_hits(linked_accounts=linked_accounts)
        if raid_hits_to_do != "":
            embed.add_field(name="Raid Hits", value=raid_hits_to_do, inline=False)

        '''clangames_to_do = await self.get_clan_games(linked_accounts=linked_accounts)
        if clangames_to_do != "":
            embed.add_field(name="Clan Games", value=clangames_to_do, inline=False)'''

        inactive_to_do = await self.get_inactive(linked_accounts=linked_accounts)
        if inactive_to_do != "":
            embed.add_field(name="Inactive Accounts (48+ hr)", value=inactive_to_do, inline=False)

        if len(embed.fields) == 0:
            embed.description = "You're all caught up chief!"

        return embed

    async def get_war_hits(self, linked_accounts: List[MyCustomPlayer]):
        async def get_clan_wars(clan_tag, player):
            war = await self.bot.get_clanwar(clanTag=clan_tag)
            if war is not None and str(war.state) == "notInWar":
                war = None
            if war is not None and war.end_time.seconds_until <= 0:
                war = None
            return (player, war)

        tasks = []
        for player in linked_accounts:
            if player.clan is not None:
                task = asyncio.ensure_future(get_clan_wars(clan_tag=player.clan.tag, player=player))
                tasks.append(task)
        wars = await asyncio.gather(*tasks)

        war_hits = ""
        for player, war in wars:
            if war is None:
                continue
            war: coc.ClanWar
            our_player = coc.utils.get(war.members, tag=player.tag)
            if our_player is None:
                continue
            attacks = our_player.attacks
            required_attacks = war.attacks_per_member
            if len(attacks) < required_attacks:
                war_hits += f"({len(attacks)}/{required_attacks}) | <t:{int(war.end_time.time.replace(tzinfo=utc).timestamp())}:R> - {player.name}\n"
        return war_hits


    async def get_legend_hits(self, linked_accounts: List[MyCustomPlayer]):
        legend_hits_remaining = ""
        for player in linked_accounts:
            if player.is_legends():
                if player.legend_day().num_attacks.integer < 8:
                    legend_hits_remaining += f"({player.legend_day().num_attacks.integer}/8) - {player.name}\n"
        return legend_hits_remaining


    async def get_raid_hits(self, linked_accounts: List[MyCustomPlayer]):
        async def get_raid(clan_tag, player):
            if player.town_hall <= 5:
                return (player, None)
            weekend = gen_raid_weekend_datestrings(number_of_weeks=1)[0]
            weekend_raid_entry = await get_raidlog_entry(clan=player.clan, weekend=weekend, bot=self.bot, limit=2)
            if weekend_raid_entry is not None and str(weekend_raid_entry.state) == "ended":
                weekend_raid_entry = None
            return (player, weekend_raid_entry)

        tasks = []
        for player in linked_accounts:
            if player.clan is not None:
                task = asyncio.ensure_future(get_raid(clan_tag=player.clan.tag, player=player))
                tasks.append(task)
        wars = await asyncio.gather(*tasks)

        raid_hits = ""
        for player, raid_log_entry in wars:
            if raid_log_entry is None:
                continue
            raid_log_entry: RaidLogEntry
            our_player = coc.utils.get(raid_log_entry.members, tag=player.tag)
            if our_player is None:
                attacks = 0
                required_attacks = 6
            else:
                attacks = our_player.attack_count
                required_attacks = our_player.attack_limit + our_player.bonus_attack_limit
            if attacks < required_attacks:
                raid_hits += f"({attacks}/{required_attacks}) - {player.name}\n"
        return raid_hits


    async def get_inactive(self, linked_accounts: List[MyCustomPlayer]):
        now = int(datetime.now(tz=utc).timestamp())
        inactive_text = ""
        for player in linked_accounts:
            last_online = player.last_online
            #48 hours in seconds
            if last_online is None:
                continue
            if now - last_online >= (48 * 60 * 60):
                inactive_text += f"<t:{last_online}:R> - {player.name}\n"
        return inactive_text


    async def get_clan_games(self, linked_accounts: List[MyCustomPlayer]):
        missing_clan_games = ""
        if self.is_clan_games():
            for player in linked_accounts:
                points = player.clan_games()
                if points < 4000:
                    missing_clan_games += f"({points}/4000) - {player.name}\n"

        return missing_clan_games


    def is_clan_games(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        year = now.year
        month = now.month
        day = now.day
        hour = now.hour
        first = datetime(year, month, 22, hour=8, tzinfo=utc)
        end = datetime(year, month, 28, hour=8, tzinfo=utc)
        if (day >= 22 and day <= 28):
            if (day == 22 and hour < 8) or (day == 28 and hour >= 8):
                is_games = False
            else:
                is_games = True
        else:
            is_games = False
        return is_games

    # UTILS
    async def create_player_hr(self, player: MyCustomPlayer, start_date, end_date):
        embed = disnake.Embed(title=f"{player.name} War Stats", colour=disnake.Color.green())
        time_range = f"{datetime.fromtimestamp(start_date).strftime('%m/%d/%y')} - {datetime.fromtimestamp(end_date).strftime('%m/%d/%y')}"
        embed.set_footer(icon_url=player.town_hall_cls.image_url, text=time_range)
        hitrate = await player.hit_rate(start_timestamp=start_date, end_timestamp=end_date)
        hr_text = ""
        for hr in hitrate:
            hr_type = f"{hr.type}".ljust(5)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            hr_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if hr_text == "":
            hr_text = "No war hits tracked.\n"
        embed.add_field(name="**Triple Hit Rate**", value=hr_text + "­\n", inline=False)

        defrate = await player.defense_rate(start_timestamp=start_date, end_timestamp=end_date)
        def_text = ""
        for hr in defrate:
            hr_type = f"{hr.type}".ljust(5)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            def_text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if def_text == "":
            def_text = "No war defenses tracked.\n"
        embed.add_field(name="**Triple Defense Rate**", value=def_text + "­\n", inline=False)

        text = ""
        hr = hitrate[0]
        footer_text = f"Avg. Off Stars: `{round(hr.average_stars, 2)}`"
        if hr.total_zeros != 0:
            hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
            text += f"`Off 0 Stars` | `{hr_nums}` | {round(hr.average_zeros * 100, 1)}%\n"
        if hr.total_ones != 0:
            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
            text += f"`Off 1 Stars` | `{hr_nums}` | {round(hr.average_ones * 100, 1)}%\n"
        if hr.total_twos != 0:
            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
            text += f"`Off 2 Stars` | `{hr_nums}` | {round(hr.average_twos * 100, 1)}%\n"
        if hr.total_triples != 0:
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`Off 3 Stars` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"

        hr = defrate[0]
        footer_text += f"\nAvg. Def Stars: `{round(hr.average_stars, 2)}`"
        if hr.total_zeros != 0:
            hr_nums = f"{hr.total_zeros}/{hr.num_attacks}".center(5)
            text += f"`Def 0 Stars` | `{hr_nums}` | {round(100 - (hr.average_zeros * 100), 1)}%\n"
        if hr.total_ones != 0:
            hr_nums = f"{hr.total_ones}/{hr.num_attacks}".center(5)
            text += f"`Def 1 Stars` | `{hr_nums}` | {round(100 - (hr.average_ones * 100), 1)}%\n"
        if hr.total_twos != 0:
            hr_nums = f"{hr.total_twos}/{hr.num_attacks}".center(5)
            text += f"`Def 2 Stars` | `{hr_nums}` | {round(100 - (hr.average_twos * 100), 1)}%\n"
        if hr.total_triples != 0:
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`Def 3 Stars` | `{hr_nums}` | {round(100 - (hr.average_triples * 100), 1)}%\n"

        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**Star Count %'s**", value=text + "­\n", inline=False)

        fresh_hr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
        nonfresh_hr = await player.hit_rate(fresh_type=[False], start_timestamp=start_date, end_timestamp=end_date)
        fresh_dr = await player.hit_rate(fresh_type=[True], start_timestamp=start_date, end_timestamp=end_date)
        nonfresh_dr = await player.defense_rate(fresh_type=[False], start_timestamp=start_date,
                                                end_timestamp=end_date)
        hitrates = [fresh_hr, nonfresh_hr, fresh_dr, nonfresh_dr]
        names = ["Fresh HR", "Non-Fresh HR", "Fresh DR", "Non-Fresh DR"]
        text = ""
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(12)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**Fresh/Not Fresh**", value=text + "­\n", inline=False)

        random = await player.hit_rate(war_types=["random"], start_timestamp=start_date, end_timestamp=end_date)
        cwl = await player.hit_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
        friendly = await player.hit_rate(war_types=["friendly"], start_timestamp=start_date, end_timestamp=end_date)
        random_dr = await player.defense_rate(war_types=["random"], start_timestamp=start_date,
                                              end_timestamp=end_date)
        cwl_dr = await player.defense_rate(war_types=["cwl"], start_timestamp=start_date, end_timestamp=end_date)
        friendly_dr = await player.defense_rate(war_types=["friendly"], start_timestamp=start_date,
                                                end_timestamp=end_date)
        hitrates = [random, cwl, friendly, random_dr, cwl_dr, friendly_dr]
        names = ["War HR", "CWL HR", "Friendly HR", "War DR", "CWL DR", "Friendly DR"]
        text = ""
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(11)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**War Type**", value=text + "­\n", inline=False)

        war_sizes = list(range(5, 55, 5))
        hitrates = []
        for size in war_sizes:
            hr = await player.hit_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
            hitrates.append(hr)
        for size in war_sizes:
            hr = await player.defense_rate(war_sizes=[size], start_timestamp=start_date, end_timestamp=end_date)
            hitrates.append(hr)

        text = ""
        names = [f"{size}v{size} HR" for size in war_sizes] + [f"{size}v{size} DR" for size in war_sizes]
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(8)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**War Size**", value=text + "­\n", inline=False)

        lost_hr = await player.hit_rate(war_statuses=["lost", "losing"], start_timestamp=start_date,
                                        end_timestamp=end_date)
        win_hr = await player.hit_rate(war_statuses=["winning", "won"], start_timestamp=start_date,
                                       end_timestamp=end_date)
        lost_dr = await player.defense_rate(war_statuses=["lost", "losing"], start_timestamp=start_date,
                                            end_timestamp=end_date)
        win_dr = await player.defense_rate(war_statuses=["winning", "won"], start_timestamp=start_date,
                                           end_timestamp=end_date)
        hitrates = [lost_hr, win_hr, lost_dr, win_dr]
        names = ["Losing HR", "Winning HR", "Losing DR", "Winning DR"]
        text = ""
        for count, hr in enumerate(hitrates):
            hr = hr[0]
            if hr.num_attacks == 0:
                continue
            hr_type = f"{names[count]}".ljust(11)
            hr_nums = f"{hr.total_triples}/{hr.num_attacks}".center(5)
            text += f"`{hr_type}` | `{hr_nums}` | {round(hr.average_triples * 100, 1)}%\n"
        if text == "":
            text = "No attacks/defenses yet.\n"
        embed.add_field(name="**War Status**", value=text + "­\n", inline=False)
        embed.description = footer_text

        return embed

    def player_components(self, players: List[MyCustomPlayer]):
        player_results = []
        if len(players) == 1:
            return player_results
        for count, player in enumerate(players):
            player_results.append(
                disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                     value=f"{count}"))
        profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        return [st2]


    # AUTOCOMPLETES
    @war_stats_player.autocomplete("start_date")
    @war_stats_player.autocomplete("end_date")
    async def date_autocomp(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        today = date.today()
        date_list = [today - timedelta(days=day) for day in range(365)]
        return [dt.strftime("%d %B %Y") for dt in date_list if
                query.lower() in str(dt.strftime("%d %B, %Y")).lower()][:25]


    @invite.autocomplete("player_tag")
    @lookup.autocomplete("tag")
    @upgrades.autocomplete("player_tag")
    @war_stats_player.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names


def setup(bot: CustomClient):
    bot.add_cog(profiles(bot))