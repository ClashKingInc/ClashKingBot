from typing import List
from CustomClasses.CustomBot import CustomClient
from utility.clash.other import gen_season_start_end_as_iso
from utility.general import get_guild_icon, create_superscript
from collections import defaultdict, namedtuple
from exceptions.CustomExceptions import MessageException
import disnake
import coc
import pendulum as pend

def war_type_convert(war_types: str) -> List[str]:
    if war_types == "all":
        war_types = ["random", "friendly", "cwl"]
    elif war_types == "war&cwl":
        war_types = ["random", "cwl"]
    else:
        if war_types == "war":
            war_types = "random"
        war_types = [war_types]
    return war_types

async def get_wars(bot: CustomClient, clan_tags: List[str], season: str | None, num_wars: int | None, num_days: int | None):
    clan_wars = []
    if num_wars is None and num_days is None:
        season = season or bot.gen_season_date()
        SEASON_START, SEASON_END = gen_season_start_end_as_iso(season=season)
        clan_wars = await bot.clan_wars.find({
            "$and": [
                {'$or': [{'data.clan.tag': {'$in': clan_tags}},
                         {'data.opponent.tag': {'$in': clan_tags}}]},
                {"data.preparationStartTime": {"$gte": SEASON_START}}, {"data.preparationStartTime": {"$lte": SEASON_END}}]
        }, projection={"data": 1, "_id": 0}).to_list(length=None)
    elif num_wars is not None:
        clan_wars = await bot.clan_wars.find({
            "$and": [{'$or': [{'data.clan.tag': {'$in': clan_tags}}, {'data.opponent.tag': {'$in': clan_tags}}]}]
        }, projection={"data": 1, "_id": 0}).sort("data.preparationStartTime", -1).limit(num_wars).to_list(length=None)
    elif num_days is not None:
        now = pend.now(tz=pend.UTC)
        days_ago = now.subtract(days=num_days)
        clan_wars = await bot.clan_wars.find({
            "$and": [
                {'$or': [{'data.clan.tag': {'$in': clan_tags}},
                         {'data.opponent.tag': {'$in': clan_tags}}]},
                {"data.preparationStartTime": {"$gte": days_ago.strftime('%Y%m%dT%H%M%S.000Z')}}]
        }, projection={"data": 1, "_id": 0}).to_list(length=None)
    return clan_wars


def star_filter_convert(star_filter: str):
    stars = star_filter.replace(" ", '').split(",")
    return [int(s) for s in stars]


async def war_hitrate(bot: CustomClient, clan: coc.Clan | None, server: disnake.Guild | None,
                      th_filter: str | None, star_filter: str, limit: int, min_attacks: int,
                      war_types: str, season: str | None, num_wars: int | None, num_days: int | None, embed_color: disnake.Color):
    if clan is None:
        clan_tags = await bot.clan_db.distinct("tag", filter={"server": server.id})
    else:
        clan_tags = [clan.tag]
    if not clan_tags:
        raise MessageException("No clans found")

    war_types = war_type_convert(war_types)
    star_filter = star_filter_convert(star_filter)

    clan_wars = await get_wars(bot=bot, clan_tags=clan_tags, season=season, num_wars=num_wars, num_days=num_days)
    hit_rate_dict = defaultdict(lambda : defaultdict(int))
    tag_to_name_map = {}
    tag_to_th_map = {}
    for war in clan_wars:
        main_clan = war.get("data").get("clan").get("tag")
        if war.get("data").get("opponent").get("tag") in clan_tags:
            main_clan = war.get("data").get("opponent").get("tag")
        coc_war = coc.ClanWar(data=war.get("data"), client=None, clan_tag=main_clan)
        if coc_war.type.lower() not in war_types:
            continue
        for attack in coc_war.clan.attacks:
            tag_to_name_map[attack.attacker_tag] = attack.attacker.name
            tag_to_th_map[attack.attacker_tag] = attack.attacker.town_hall
            if th_filter == "all":
                hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                hit_rate_dict[attack.attacker_tag]["total"] += 1
            elif th_filter == "equalthonly":
                if attack.attacker.town_hall == attack.defender.town_hall:
                    hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                    hit_rate_dict[attack.attacker_tag]["total"] += 1
            elif "v" in th_filter:
                th, def_th = th_filter.split("v")
                if attack.attacker.town_hall == int(th) and attack.defender.town_hall == int(def_th):
                    hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                    hit_rate_dict[attack.attacker_tag]["total"] += 1
            else:
                if attack.attacker.town_hall == int(th_filter):
                    hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                    hit_rate_dict[attack.attacker_tag]["total"] += 1

    holder_list = []
    holder = namedtuple("holder", ["name", "tag", "townhall", "hitrate", "attacks", "total"])
    for tag, data in hit_rate_dict.items():
        total_attacks = data.get("total", 0)
        if total_attacks == 0:
            continue
        hr_attack_total = sum([data.get(star, 0) for star in star_filter])
        holder_list.append(holder(name=tag_to_name_map.get(tag), tag=tag, townhall=tag_to_th_map.get(tag),
                                  hitrate=round((hr_attack_total/ total_attacks) * 100),
                                  attacks=hr_attack_total,
                                  total=total_attacks
                                  ))
    holder_list = [h for h in holder_list if h.total >= min_attacks]
    holder_list.sort(key=lambda x : x.hitrate, reverse=True)
    text = "`  # Perc  Atks Name`\n"
    for count, player in enumerate(holder_list[:limit], 1):
        count = f"{count}"
        div_text = f"{player.attacks}/{player.total}"
        text += f"{bot.fetch_emoji(player.townhall)}`{count:<2}{player.hitrate:>3}% {div_text:^5} {player.name[:13]}`\n"

    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"{(clan or server).name} Top {limit} Hitrate", icon_url=get_guild_icon(server) if clan is None else clan.badge.url)
    if season:
        f_text = f"{season} | {len(clan_wars)} wars"
    elif num_wars:
        f_text = f"{len(clan_wars)} wars"
    elif num_days:
        f_text = f"{num_days} days | {len(clan_wars)} wars"
    embed.set_footer(text=f"{f_text} | Stars: {str(star_filter)}\nWar Types: {str(war_types)} | TH Filter: {th_filter}")
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed


async def war_hitcount(bot: CustomClient, clan_tags: List[str], season: str, th_filter: str | None, limit: int, war_types: str, embed_color: disnake.Color):
    season = season or bot.gen_season_date()

    if war_types == "all":
        war_types = ["random", "friendly", "cwl"]
    elif war_types == "war&cwl":
        war_types = ["random", "cwl"]
    else:
        if war_types == "war":
            war_types = "random"
        war_types = [war_types]
    SEASON_START, SEASON_END = gen_season_start_end_as_iso(season=season)
    clan_wars = await bot.clan_wars.find({
        "$and": [
            {'$or': [{'data.clan.tag': {'$in': clan_tags}},
                     {'data.opponent.tag': {'$in': clan_tags}}]},
            {"data.preparationStartTime": {"$gte": SEASON_START}}, {"data.preparationStartTime": {"$lte": SEASON_END}}]
    }, projection={"data": 1, "_id": 0}).to_list(length=None)
    hit_rate_dict = defaultdict(lambda : defaultdict(int))
    tag_to_name_map = {}
    tag_to_th_map = {}
    for war in clan_wars:
        main_clan = war.get("data").get("clan").get("tag")
        if war.get("data").get("opponent").get("tag") in clan_tags:
            main_clan = war.get("data").get("opponent").get("tag")
        coc_war = coc.ClanWar(data=war.get("data"), client=None, clan_tag=main_clan)
        if coc_war.type.lower() not in war_types:
            continue
        for attack in coc_war.clan.attacks:
            tag_to_name_map[attack.attacker_tag] = attack.attacker.name
            tag_to_th_map[attack.attacker_tag] = attack.attacker.town_hall
            if th_filter == "all":
                hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                hit_rate_dict[attack.attacker_tag]["total"] += 1
            elif th_filter == "equalthonly":
                if attack.attacker.town_hall == attack.defender.town_hall:
                    hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                    hit_rate_dict[attack.attacker_tag]["total"] += 1
            else:
                th, def_th = th_filter.split("v")
                if attack.attacker.town_hall == int(th) and attack.defender.town_hall == int(def_th):
                    hit_rate_dict[attack.attacker_tag][attack.stars] += 1
                    hit_rate_dict[attack.attacker_tag]["total"] += 1

    holder_list = []
    holder = namedtuple("holder", ["name", "tag", "townhall", "hitrate_0", "hitrate_1", "hitrate_2", "hitrate_3"])
    for tag, data in hit_rate_dict.items():
        total_attacks = data.get("total", 0)
        if total_attacks == 0:
            continue
        holder_list.append(holder(name=tag_to_name_map.get(tag), tag=tag, townhall=tag_to_th_map.get(tag),
                                  hitrate_0=data.get(0, 0),
                                  hitrate_1=data.get(1, 0),
                                  hitrate_2=data.get(2, 0),
                                  hitrate_3=data.get(3, 0)
                                  ))
    holder_list.sort(key=lambda x : (x.hitrate_3, x.hitrate_2, x.hitrate_1), reverse=True)
    text = "`#  TH 1★ 2★ 3★   Name`\n"
    for count, player in enumerate(holder_list[:limit], 1):
        text += f"`{count:<2} {player.townhall:>2} {player.hitrate_1:>2} {player.hitrate_2:>2} {player.hitrate_3:>2} {player.name[:13]}`\n"

    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"Top {limit} Hitcount ({season})", icon_url=get_guild_icon(None))
    embed.timestamp = pend.now(tz=pend.UTC)
    return embed

