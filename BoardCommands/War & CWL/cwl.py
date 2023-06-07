
import coc
import disnake
from disnake.ext import commands
from datetime import datetime
from utils.clash import cwl_league_emojis
from utils.discord_utils import partial_emoji_gen
from Assets.emojiDictionary import emojiDictionary
from collections import defaultdict
from typing import List
from coc import utils
from CustomClasses.CustomBot import CustomClient
from utils.general import create_superscript
from pytz import utc
from utils.constants import leagues, war_leagues
import operator
import asyncio
import re
import calendar





class Cwl(commands.Cog, name="CWL"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    async def season_convertor(self, season: str):
        if season is not None:
            if len(season.split("|")) == 2:
                season = season.split("|")[0]
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            season_date = f"{end_date.year}-{month}"
        else:
            season_date = self.bot.gen_season_date()
        return season_date

    @commands.slash_command(name="cwl", description="Stats, stars, and more for a clan's cwl")
    async def cwl(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter),
                  season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        await ctx.response.defer()
        asyncio.create_task(self.bot.store_all_cwls(clan=clan))
        (group, clan_league_wars, fetched_clan, war_league) = await self.get_cwl_wars(clan=clan, season=season)

        if not clan_league_wars:
            embed = disnake.Embed(description=f"[**{clan.name}**]({clan.share_link}) is not in CWL.",
                                  color=disnake.Color.green())
            embed.set_thumbnail(url=clan.badge.large)
            return await ctx.send(embed=embed)

        overview_round = self.get_latest_war(clan_league_wars=clan_league_wars)
        ROUND = overview_round; CLAN = clan; PAGE = "cwlround_overview"

        (current_war, next_war) = self.get_wars_at_round(clan_league_wars=clan_league_wars, round=ROUND)
        dropdown = await self.component_handler(page=PAGE, current_war=current_war, next_war=next_war, group=group, league_wars=clan_league_wars, fetched_clan=fetched_clan)
        embeds = await self.page_manager(page=PAGE, group=group, war=current_war, next_war=next_war, league_wars=clan_league_wars, clan=CLAN, fetched_clan=fetched_clan, war_league=war_league)

        await ctx.send(embeds=embeds, components=dropdown)
        msg = await ctx.original_message()
        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id


        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            await res.response.defer()
            if "cwlchoose_" in res.values[0]:
                clan_tag = (str(res.values[0]).split("_"))[-1]
                CLAN = await self.bot.getClan(clan_tag)
                (group, clan_league_wars, x, y) = await self.get_cwl_wars(clan=CLAN, season=season, group=group, fetched_clan=fetched_clan)
                PAGE = "cwlround_overview"; ROUND = self.get_latest_war(clan_league_wars=clan_league_wars)

            elif "cwlround_" in res.values[0]:
                round = res.values[0].split("_")[-1]
                if round != "overview":
                    PAGE = "round"; ROUND = int(round) - 1
                else:
                    PAGE = "cwlround_overview"; ROUND = overview_round

            elif res.values[0] == "excel":
                await res.send(content="Coming Soon!", ephemeral=True)
                continue
            else:
                PAGE = res.values[0]

            (current_war, next_war) = self.get_wars_at_round(clan_league_wars=clan_league_wars, round=ROUND)
            embeds = await self.page_manager(page=PAGE, group=group, war=current_war, next_war=next_war, league_wars=clan_league_wars,
                                             clan=CLAN, fetched_clan=fetched_clan, war_league=war_league)
            dropdown = await self.component_handler(page=PAGE, current_war=current_war, next_war=next_war, group=group, league_wars=clan_league_wars, fetched_clan=fetched_clan)

            await res.edit_original_message(embeds=embeds, components=dropdown)

    def get_latest_war(self, clan_league_wars: List[coc.ClanWar]):
        last_prep = None
        last_current = None
        for count, war in enumerate(clan_league_wars):
            if war.state == "preperation":
                last_prep = count
            elif war.state == "inWar":
                last_current = count
        if last_current is None:
            last_current = last_prep
        if last_current is None:
            last_current = len(clan_league_wars) - 1
        return last_current

    def get_wars_at_round(self, clan_league_wars: List[coc.ClanWar], round: int):
        current_war = clan_league_wars[round]
        try:
            next_war = clan_league_wars[round + 1]
        except:
            next_war = None
        return (current_war, next_war)

    async def get_cwl_wars(self, clan: coc.Clan, season: str, group=None, fetched_clan=None):
        clan_league_wars = []
        clan_tag = clan.tag
        try:
            if group is None:
                group = await self.bot.coc_client.get_league_group(clan.tag)
            if group.season != season:
                raise Exception
            async for w in group.get_wars_for_clan(clan.tag):
                clan_league_wars.append(w)
            if clan_league_wars:
                return (group, clan_league_wars, None, clan.war_league)
        except:
            pass

        print("here")
        if not clan_league_wars:
            if fetched_clan is not None:
                clan_tag = fetched_clan
            response = await self.bot.cwl_db.find_one({"clan_tag": clan_tag, "season": season})
            if fetched_clan is not None:
                print(response)
            if response is not None:
                group = coc.ClanWarLeagueGroup(data=response.get("data"), client=self.bot.coc_client)
                clan_league_wars = self.wars_from_group(data=response.get("data"), clan_tag=clan.tag, group=group)
                if clan_league_wars:
                    league_name = [x["name"]for x in war_leagues["items"] if x["id"] == response.get("data").get("leagueId")][0]
                    return (group, clan_league_wars, clan.tag, league_name)
            else:
                return (None, [], None, None)

    async def page_manager(self, page:str, group: coc.ClanWarLeagueGroup, war: coc.ClanWar, next_war: coc.ClanWar,
                           league_wars: List[coc.ClanWar], clan: coc.Clan, fetched_clan: str, war_league: str):
        if page == "cwlround_overview":
            war_cog = self.bot.get_cog(name="War")
            embed = await war_cog.main_war_page(war=war, war_league=war_league)
            return [embed]
        elif page == "round":
            war_cog = self.bot.get_cog(name="War")
            embed = await war_cog.main_war_page(war=war, war_league=war_league)
            return [embed]
        elif page == "nextround":
            war_cog = self.bot.get_cog(name="War")
            embed = await war_cog.main_war_page(war=next_war, war_league=war_league)
            return [embed]
        elif page == "lineup":
            embed1 = await self.roster_embed(next_war)
            embed2 = await self.opp_roster_embed(next_war)
            return[embed1, embed2]
        elif page == "stars":
            embed = await self.star_lb(league_wars, clan)
            embed2 = await self.star_lb(league_wars, clan, defense=True)
            return[embed, embed2]
        elif page == "rankings":
            embed = await self.ranking_lb(group, fetched_clan)
            return [embed]
        elif page == "allrounds":
            embed = await self.all_rounds(league_wars, clan)
            return [embed]
        elif page == "all_members":
            embed = await self.all_members(group, clan)
            return [embed]
        elif page == "current_lineup":
            embed1 = await self.roster_embed(war)
            embed2 = await self.opp_roster_embed(war)
            return [embed1, embed2]
        elif page == "attacks":
            embed = await self.attacks_embed(war=war)
            return [embed]
        elif page == "defenses":
            embed = await self.defenses_embed(war=war)
            return [embed]
        elif page == "nextopp_overview":
            embed = await self.opp_overview(war=war)
            return [embed]
        elif page == "missedhits":
            embed = await self.missed_hits(league_wars=league_wars, clan=clan)
            return [embed]

    def wars_from_group(self, group: coc.ClanWarLeagueGroup, data: dict, clan_tag=None):
        rounds = data.get("rounds")
        list_wars = []
        for round in rounds:
            for war in round.get("wars"):
                if clan_tag is None or war.get("clan").get("tag") == clan_tag or war.get("opponent").get("tag") == clan_tag:
                    #print(war["endTime"])
                    war["endTime"] = datetime.fromtimestamp(war["endTime"]/1000).strftime('%Y%m%dT%H%M%S.000Z')
                    war["startTime"] = datetime.fromtimestamp(war["startTime"]/1000).strftime('%Y%m%dT%H%M%S.000Z')
                    war["preparationStartTime"] = datetime.fromtimestamp(war["preparationStartTime"]/1000).strftime('%Y%m%dT%H%M%S.000Z')
                    for member in (war.get("clan").get("members") + war.get("opponent").get("members")):
                        if member.get("bestOpponentAttack") is None:
                            member["bestOpponentAttack"] = {}
                        member["townhallLevel"] = member["townHallLevel"]
                        if member.get("mapPosition") is None:
                            member["mapPosition"] = 1
                        if member.get("attack"):
                            attack = member.get("attack")
                            attack["duration"] = 0
                            member["attacks"] = [attack]
                    list_wars.append(coc.ClanWar(data=war, clan_tag=clan_tag, client=self.bot.coc_client, league_group=group))
        return list_wars

    def get_league_war_by_tag(self, league_wars: List[coc.ClanWar], war_tag: str):
        for war in league_wars:
            if war.war_tag == war_tag:
                return war


    #COMPONENTS
    async def component_handler(self, page: str, current_war: coc.ClanWar, next_war: coc.ClanWar, group: coc.ClanWarLeagueGroup, league_wars: List[coc.ClanWar], fetched_clan):
        round_stat_dropdown = await self.stat_components(war=current_war, next_war=next_war)
        overall_stat_dropdown = await self.overall_stat_components()
        clan_dropdown = await self.clan_components(group=group)
        round_dropdown = await self.round_components(league_wars=league_wars)
        r = None
        if "cwlround_" in page:
            round = page.split("_")[-1]
            if round == "overview":
                r = [overall_stat_dropdown, round_dropdown, clan_dropdown]
        elif page in ["stars", "rankings", "allrounds", "all_members", "excel", "missedhits"]:
            r =  [overall_stat_dropdown, round_dropdown, clan_dropdown]
        else:
            r =  [round_stat_dropdown, round_dropdown, clan_dropdown]
        if fetched_clan is not None:
            r = r[:-1]
        return r


    async def overall_stat_components(self):
        map = partial_emoji_gen(self.bot, "<:map:944913638500761600>")
        star = partial_emoji_gen(self.bot, "<:star:825571962699907152>")
        up = partial_emoji_gen(self.bot, "<:warwon:932212939899949176>")

        options = [  # the options in your dropdown
            disnake.SelectOption(label="Star Leaderboard", emoji=star, value="stars"),
            disnake.SelectOption(label="Clan Rankings", emoji=up, value="rankings"),
            disnake.SelectOption(label="Missed Hits", emoji=self.bot.emoji.no.partial_emoji, value="missedhits"),
            disnake.SelectOption(label="All Rounds", emoji=map, value="allrounds"),
            disnake.SelectOption(label="All Members", emoji=self.bot.emoji.alphabet.partial_emoji, value="all_members"),
            disnake.SelectOption(label="Excel Export", emoji=self.bot.emoji.excel.partial_emoji, value="excel")
        ]

        select = disnake.ui.Select(
            options=options,
            placeholder="Overview Pages",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        return disnake.ui.ActionRow(select)

    async def stat_components(self, war: coc.ClanWar, next_war: coc.ClanWar):
        swords = partial_emoji_gen(self.bot, "<a:swords:944894455633297418>", animated=True)
        troop = partial_emoji_gen(self.bot, "<:troop:861797310224400434>")
        options = []

        # on first round - only next round
        # on last round - only current round
        if war is None:
            options.insert(0, disnake.SelectOption(label="Next Round", emoji=self.bot.emoji.right_green_arrow.partial_emoji, value="nextround"))
            options.insert(1, disnake.SelectOption(label="Next Round Lineup", emoji=troop, value="lineup"))
        elif next_war is None:
            options.insert(0, disnake.SelectOption(label="Current Round", emoji=swords, value="round"))
            options.insert(1, disnake.SelectOption(label="Current Lineup", emoji=troop, value="current_lineup"))
            options.insert(2, disnake.SelectOption(label="Attacks", emoji=self.bot.emoji.thick_sword.partial_emoji, value="attacks"))
            options.insert(3, disnake.SelectOption(label="Defenses", emoji=self.bot.emoji.shield.partial_emoji, value="defenses"))
        else:
            options.insert(0, disnake.SelectOption(label="Current Round", emoji=swords, value="round"))
            options.insert(1, disnake.SelectOption(label="Current Lineup", emoji=troop, value="current_lineup"))
            options.insert(2, disnake.SelectOption(label="Attacks", emoji=self.bot.emoji.thick_sword.partial_emoji,value="attacks"))
            options.insert(3, disnake.SelectOption(label="Defenses", emoji=self.bot.emoji.shield.partial_emoji,value="defenses"))

            options.insert(4, disnake.SelectOption(label="Next Round", emoji=self.bot.emoji.right_green_arrow.partial_emoji, value="nextround"))
            options.insert(5, disnake.SelectOption(label="Next Round Lineup", emoji=troop, value="lineup"))
            options.insert(6, disnake.SelectOption(label="Next Opponent Overview", emoji=self.bot.emoji.magnify_glass.partial_emoji, value="nextopp_overview"))

        select = disnake.ui.Select(
            options=options,
            placeholder="Round Stat Pages",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        return disnake.ui.ActionRow(select)

    async def round_components(self, league_wars: List[coc.ClanWar]):
        options = [disnake.SelectOption(label=f"Overview", value=f"cwlround_overview")]
        for round in range(1, len(league_wars) + 1):
            options.append(disnake.SelectOption(label=f"Round {round}", value=f"cwlround_{round}"))

        select = disnake.ui.Select(
            options=options,
            placeholder="Choose a round",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        return disnake.ui.ActionRow(select)

    async def clan_components(self, group: coc.ClanWarLeagueGroup):
        options = []
        for clan in group.clans:
            options.append(
                disnake.SelectOption(label=f"{clan.name}", value=f"cwlchoose_{clan.tag}"))

        select = disnake.ui.Select(
            options=options,
            placeholder="Choose a clan",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        return disnake.ui.ActionRow(select)

    async def attacks_embed(self, war: coc.ClanWar):
        attacks = ""
        missing_attacks = []
        miss_attack_text = ""
        for player in war.members:
            if player not in war.opponent.members:
                if player.attacks == []:
                    miss_attack = f"➼ {self.bot.fetch_emoji(name=player.town_hall)}{player.name}\n"
                    if len(miss_attack) + len(miss_attack_text) >= 1024:
                        missing_attacks.append(miss_attack_text)
                        miss_attack_text = ""
                    miss_attack_text += miss_attack
                    continue
                name = player.name
                attacks += f"\n{self.bot.fetch_emoji(name=player.town_hall)}**{name}**"
                for a in player.attacks:
                    star_str = ""
                    stars = a.stars
                    for x in range(0, stars):
                        star_str += "★"
                    for x in range(0, 3 - stars):
                        star_str += "☆"

                    base = create_superscript(a.defender.map_position)
                    attacks += f"\n➼ {a.destruction}%{star_str}{base}"

        embed = disnake.Embed(title=f"{war.clan.name} War Attacks", description=attacks,
                              color=disnake.Color.green())
        if miss_attack_text != "":
            missing_attacks.append(miss_attack_text)
        if missing_attacks:
            for m in missing_attacks:
                embed.add_field(name="**No attacks done:**", value=m)
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def defenses_embed(self, war: coc.ClanWar):
        defenses = ""
        missing_defenses = []
        miss_def_text = ""
        for player in war.clan.members:
            if player.defenses == []:
                miss_attack = f"➼ {self.bot.fetch_emoji(name=player.town_hall)}{player.name}\n"
                if len(miss_attack) + len(miss_def_text) >= 1024:
                    missing_defenses.append(miss_def_text)
                    miss_def_text = ""
                miss_def_text += miss_attack
                continue
            name = player.name
            defenses += f"\n{self.bot.fetch_emoji(name=player.town_hall)}**{name}**"
            for a in player.defenses:
                star_str = ""
                stars = a.stars
                for x in range(0, stars):
                    star_str += "★"
                for x in range(0, 3 - stars):
                    star_str += "☆"

                base = create_superscript(a.defender.map_position)
                defenses += f"\n➼ {a.destruction}%{star_str}{base}"

        embed = disnake.Embed(title=f"{war.clan.name} Defenses Taken", description=defenses,
                              color=disnake.Color.green())

        if miss_def_text != "":
            missing_defenses.append(miss_def_text)
        if missing_defenses:
            for d in missing_defenses:
                embed.add_field(name="**No defenses taken:**", value=d)
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def opp_overview(self, war: coc.ClanWar):
        clan = await self.bot.getClan(war.opponent.tag)
        leader = utils.get(clan.members, role=coc.Role.leader)

        if clan.public_war_log:
            warwin = clan.war_wins
            warloss = clan.war_losses
            if warloss == 0:
                warloss = 1
            winstreak = clan.war_win_streak
            winrate = round((warwin / warloss), 2)
        else:
            warwin = clan.war_wins
            warloss = "Hidden Log"
            winstreak = clan.war_win_streak
            winrate = "Hidden Log"

        flag = ""
        if str(clan.location) == "International":
            flag = "<a:earth:861321402909327370>"
        else:
            flag = f":flag_{clan.location.country_code.lower()}:"
        embed = disnake.Embed(title=f"**War Opponent: {clan.name}**", description=f"Tag: [{clan.tag}]({clan.share_link})\n"
                                                                    f"Trophies: <:trophy:825563829705637889> {clan.points} | <:vstrophy:944839518824058880> {clan.versus_points}\n"
                                                                    f"Required Trophies: <:trophy:825563829705637889> {clan.required_trophies}\n"
                                                                    f"Location: {flag} {clan.location}\n\n"
                                                                    f"Leader: {leader.name}\n"
                                                                    f"Level: {clan.level} \n"
                                                                    f"Members: <:people:932212939891552256>{clan.member_count}/50\n\n"
                                                                    f"CWL: {self.leagueAndTrophies(str(clan.war_league))}{str(clan.war_league)}\n"
                                                                    f"Wars Won: <:warwon:932212939899949176>{warwin}\nWars Lost: <:warlost:932212154164183081>{warloss}\n"
                                                                    f"War Streak: <:warstreak:932212939983847464>{winstreak}\nWinratio: <:winrate:932212939908337705>{winrate}\n\n"
                                                                    f"Description: {clan.description}",
                              color=disnake.Color.green())

        embed.set_thumbnail(url=clan.badge.large)
        return embed

    async def all_members(self, group:coc.ClanWarLeagueGroup, clan: coc.Clan):
        roster = ""
        our_clan = coc.utils.get(group.clans, tag=clan.tag)
        members = our_clan.members
        tags = [member.tag for member in members]

        x = 1
        for player in await self.bot.get_players(tags):
            if player is None:
                continue
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(x) + "."
            place = place.ljust(3)
            hero_total = 0
            hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
            heros = player.heroes
            for hero in heros:
                if hero.name in hero_names:
                    hero_total += hero.level
            if hero_total == 0:
                hero_total = ""
            name = re.sub('[*_`~/]', '', player.name)
            roster += f"\u200e`{place}` {th_emoji} \u200e{name}\u200e | {hero_total}\n"
            x += 1

        embed = disnake.Embed(title=f"{clan.name} CWL Members", description=roster,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        return embed

    async def roster_embed(self, war: coc.ClanWar):
        roster = ""
        tags = []
        lineup = []
        x =0
        for player in war.members:
            if player not in war.opponent.members:
                tags.append(player.tag)
                x+=1
                lineup.append(x)

        x = 0
        async for player in self.bot.coc_client.get_players(tags):
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(lineup[x]) + "."
            place = place.ljust(3)
            hero_total = 0
            hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
            heros = player.heroes
            for hero in heros:
                if hero.name in hero_names:
                    hero_total += hero.level
            if hero_total == 0:
                hero_total = ""
            roster += f"\u200e`{place}` {th_emoji} \u200e{player.name}\u200e | {hero_total}\n"
            x += 1

        embed = disnake.Embed(title=f"{war.clan.name} War Roster", description=roster,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=war.clan.badge.large)
        return embed

    async def opp_roster_embed(self, war):
        roster = ""
        tags = []
        lineup = []
        x = 0
        for player in war.opponent.members:
            tags.append(player.tag)
            x += 1
            lineup.append(x)

        x = 0
        async for player in self.bot.coc_client.get_players(tags):
            th = player.town_hall
            th_emoji = emojiDictionary(th)
            place = str(lineup[x]) + "."
            place = place.ljust(3)
            heros = player.heroes
            hero_total = 0
            hero_names = ["Barbarian King", "Archer Queen", "Royal Champion", "Grand Warden"]
            for hero in heros:
                if hero.name in hero_names:
                    hero_total += hero.level
            if hero_total == 0:
                hero_total = ""
            roster += f"\u200e`{place}` {th_emoji} \u200e{player.name}\u200e | {hero_total}\n"
            x += 1

        embed = disnake.Embed(title=f"{war.opponent.name} War Roster", description=roster,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=war.opponent.badge.large)
        return embed

    async def star_lb(self, league_wars, clan, defense=False):
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_name = defaultdict(str)
        num_attacks_done = defaultdict(int)
        num_wars_in = defaultdict(int)
        for war in league_wars:
            war: coc.ClanWar
            if str(war.state) == "preparation":
                continue
            for player in war.members:
                num_wars_in[player.tag] += 1
                tag_to_name[player.tag] = player.name
                if player not in war.opponent.members:
                    if defense:
                        if player.defenses:
                            num_attacks_done[player.tag] += 1
                            defenses = player.defenses
                            top_defense = defenses[0]
                            for defense in defenses:
                                if defense.destruction > top_defense.destruction:
                                    top_defense = defense
                            stars = top_defense.stars
                            destruction = top_defense.destruction
                            star_dict[player.tag] += stars
                            dest_dict[player.tag] += destruction
                    else:
                        attacks = player.attacks
                        for attack in attacks:
                            num_attacks_done[player.tag] += 1
                            stars = attack.stars
                            destruction = attack.destruction
                            star_dict[player.tag] += stars
                            dest_dict[player.tag] += destruction

        star_list = []
        for tag, stars in star_dict.items():
            destruction = dest_dict[tag]
            name = tag_to_name[tag]
            hits_done = num_attacks_done[tag]
            num_wars = num_wars_in[tag]
            star_list.append([name, stars, destruction, f"{hits_done}/{num_wars}"])

        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
        text = ""
        text += f"` # HIT ST DSTR NAME           `\n"
        x = 1
        for item in sorted_list:
            name = item[0]
            stars = str(item[1])
            dest = str(item[2])
            hits_done = item[3]
            rank = str(x)
            rank = rank.rjust(2)
            stars = stars.rjust(2)
            name = name.ljust(15)
            dest = dest.rjust(3) + "%"
            text += f"`\u200e{rank} {hits_done} {stars} {dest} \u200e{name}`\n"
            x+=1

        if defense:
            ty = "Defense"
        else:
            ty = "Offense"

        embed = disnake.Embed(title=f"{clan.name} {ty} Leaderboard", description=text,
                              color=disnake.Color.green())
        return embed

    async def all_rounds(self, league_wars, clan):
        embed = disnake.Embed(title=f"{clan.name} CWL | All Rounds",
                              color=disnake.Color.green())

        r = 1
        for war in league_wars:
            war: coc.ClanWar
            war_time = war.start_time.seconds_until
            war_state = "In Prep"
            war_pos = "Starting"
            if war_time >= 0:
                war_time = war.start_time.time.replace(tzinfo=utc).timestamp()
            else:
                war_time = war.end_time.seconds_until
                if war_time <= 0:
                    war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
                    war_pos = "Ended"
                    war_state = "War Over | "
                else:
                    war_time = war.end_time.time.replace(tzinfo=utc).timestamp()
                    war_pos = "Ending"
                    war_state = "In War |"
            team_hits = f"{len(war.attacks) - len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".ljust(
                7)
            opp_hits = f"{len(war.opponent.attacks)}/{war.team_size * war.attacks_per_member}".rjust(7)
            emoji=""
            if str(war.status) == "won":
                emoji = "<:greentick:601900670823694357>"
            elif str(war.status) == "lost":
                emoji = "<:redtick:601900691312607242>"
            embed.add_field(name=f"**{war.clan.name}** vs **{war.opponent.name}**\n"
                                 f"{emoji}Round {r} | {war_state} {str(war.status).capitalize()}",
                            value=f"`{team_hits}`<a:swords:944894455633297418>`{opp_hits}`\n"
                                  f"`{war.clan.stars:<7}`<:star:825571962699907152>`{war.opponent.stars:7}`\n"
                                  f"`{round(war.clan.destruction,2):<6}%`<:broken_sword:944896241429540915>`{round(war.opponent.destruction,2):6}%`\n"
                                  f"{war_pos} <t:{int(war_time)}:R>\n­\n"
                            , inline=False)
            r+=1
        return embed

    async def missed_hits(self, league_wars, clan):
        missed_hits = defaultdict(int)
        tag_to_member = {}
        for war in league_wars:
            war: coc.ClanWar
            war_time = war.end_time.seconds_until
            if war_time <= 0:
                for member in war.clan.members:
                    if not member.attacks:
                        missed_hits[member.tag] += 1
                        tag_to_member[member.tag] = member

        text = ""
        for tag, number_missed in missed_hits.items():
            member = tag_to_member[tag]
            name = re.sub('[*_`~/]', '', member.name)
            th_emoji = emojiDictionary(member.town_hall)
            text += f"{th_emoji}{name} - {number_missed} hits\n"

        if text == "":
            text = "No Missed Hits"

        embed = disnake.Embed(title=f"{clan.name} CWL Missed Hits", description= text,color=disnake.Color.green())

        return embed

    async def ranking_lb(self, group: coc.ClanWarLeagueGroup, fetched_clan: str = None):
        star_dict = defaultdict(int)
        dest_dict = defaultdict(int)
        tag_to_name = defaultdict(str)

        league_wars = []
        if fetched_clan is not None:
            data = (await self.bot.cwl_db.find_one({"clan_tag": fetched_clan, "season": group.season})).get("data")
            league_wars = self.wars_from_group(group=group, data=data)
        rounds = group.rounds
        for round in rounds:
            for war_tag in round:
                if not league_wars:
                    war = await self.bot.coc_client.get_league_war(war_tag)
                else:
                    war = self.get_league_war_by_tag(league_wars=league_wars, war_tag=war_tag)
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
            star_list.append([name, stars, destruction])

        sorted_list = sorted(star_list, key=operator.itemgetter(1, 2), reverse=True)
        text = ""
        text += f"`# STR DSTR   NAME           `"
        x = 1
        for item in sorted_list:
            name = item[0]
            stars = str(item[1])
            dest = str(item[2])
            rank = str(x)
            rank = rank.rjust(1)
            stars = stars.rjust(2)
            name = name.ljust(15)
            dest = dest.rjust(5) + "%"
            text += f"\n`\u200e{rank} \u200e{stars} {dest} \u200e{name}`"
            x += 1

        embed = disnake.Embed(title=f"Clan Ranking Leaderboard", description=text,
                              color=disnake.Color.green())
        return embed

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
                num_def += 1
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

        avg_destr = round(destr / num_def, 2)
        avg_destr_opp = round(opp_destr / opp_num_def, 2)
        return [stars, avg_destr, opp_stars, avg_destr_opp]

    async def war_th_comps(self, war: coc.ClanWar):
        thcount = defaultdict(int)
        opp_thcount = defaultdict(int)

        for player in war.members:
            if player not in war.opponent.members:
                thcount[player.town_hall] += 1
            else:
                opp_thcount[player.town_hall] += 1

        stats = ""
        for th_level, th_count in sorted(thcount.items(), reverse=True):
            th_emoji = self.bot.fetch_emoji(th_level)
            stats += f"{th_emoji}`{th_count}` "
        opp_stats = ""
        for th_level, th_count in sorted(opp_thcount.items(), reverse=True):
            th_emoji = self.bot.fetch_emoji(th_level)
            opp_stats += f"{th_emoji}`{th_count}` "

        return [stats, opp_stats]

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

    @commands.slash_command(name="cwl-status", description="CWL spin status of clans in family")
    async def cwl_status(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"cwlstatusfam_"))
        embed = await self.create_cwl_status(guild=ctx.guild)
        await ctx.edit_original_message(embed=embed, components=[buttons])

    async def create_cwl_status(self, guild: disnake.Guild):
        now = datetime.now()
        season = self.bot.gen_season_date()
        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": guild.id})
        if len(clan_tags) == 0:
            embed = disnake.Embed(description="No clans linked to this server.", color=disnake.Color.red())
            return embed

        clans= await self.bot.get_clans(tags=clan_tags)

        spin_list = []
        for clan in clans:
            if clan is None:
                continue
            c = [clan.name, clan.war_league.name, clan.tag]
            try:
                league = await self.bot.coc_client.get_league_group(clan.tag)
                state = league.state
                if str(state) == "preparation":
                    c.append("<a:CheckAccept:992611802561134662>")
                    c.append(1)
                elif str(state) == "ended":
                    c.append("<:dash:933150462818021437>")
                    c.append(3)
                elif str(state) == "inWar":
                    c.append("<a:swords:944894455633297418>")
                    c.append(0)
                elif str(state) == "notInWar":
                    c.append("<a:spinning:992612297048588338>")
                    c.append(2)
            except coc.errors.NotFound:
                c.append("<:dash:933150462818021437>")
                c.append(3)
            spin_list.append(c)

        clans_list = sorted(spin_list, key=lambda x: (x[1], x[4]), reverse=False)

        main_embed = disnake.Embed(title=f"__**{guild.name} CWL Status**__",
                                   color=disnake.Color.green())

        #name, league, clan, status emoji, order
        for league in leagues:
            text = ""
            for clan in clans_list:
                if clan[1] == league:
                    text += f"{clan[3]} {clan[0]}\n"
                if (clan[2] == clans_list[len(clans_list) - 1][2]) and (text != ""):
                    main_embed.add_field(name=f"**{league}**", value=text, inline=False)

        main_embed.add_field(name="Legend", value=f"<a:spinning:992612297048588338> Spinning | <:dash:933150462818021437> Not Spun | <a:CheckAccept:992611802561134662> Prep |  <a:swords:944894455633297418> War")
        main_embed.timestamp = now
        main_embed.set_footer(text="Last Refreshed:")
        return main_embed

    @cwl.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        clan_list = []
        for tClan in await tracked.to_list(length=limit):
            name = tClan.get("name")
            tag = tClan.get("tag")
            if query.lower() in name.lower():
                clan_list.append(f"{name} | {tag}")
        return clan_list[0:25]

    @cwl.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        if "|" in ctx.filled_options["clan"]:
            clan = await self.bot.getClan(clan_tag=ctx.filled_options["clan"])
            if clan is None:
                seasons = self.bot.gen_season_date(seasons_ago=25)[0:]
                return [season for season in seasons if query.lower() in season.lower()]
            dates = [f"{self.bot.gen_season_date(seasons_ago=1)[0]} | {clan.war_league}"]
            cwls = await self.bot.cwl_db.find({"$and" : [{"clan_tag" : clan.tag}, {"data" : {"$ne" : None}}]},
                                              {"data.leagueId" : 1, "season" : 1}).limit(24).to_list(length=None)
            for cwl in cwls:
                league_name = next((x["name"] for x in war_leagues["items"] if x["id"] == cwl.get("data").get("leagueId")), "Unknown")
                dates.append(f"{calendar.month_name[int(cwl.get('season').split('-')[-1])]} {int(cwl.get('season').split('-')[0])} | {league_name}")
            return dates[:25]
        else:
            seasons = self.bot.gen_season_date(seasons_ago=25)[0:]
            return [season for season in seasons if query.lower() in season.lower()]

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if "cwlstatusfam_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            embed = await self.create_cwl_status(guild=ctx.guild)
            await ctx.edit_original_message(embed=embed)

def setup(bot: CustomClient):
    bot.add_cog(Cwl(bot))