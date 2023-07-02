
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





#COMPONENTS


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






