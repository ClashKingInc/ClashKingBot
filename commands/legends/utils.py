import calendar
import random
import aiohttp
import emoji
import io
import disnake
import asyncio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from CustomClasses.CustomBot import CustomClient
from CustomClasses.DatabaseClient.Classes.player import LegendPlayer, LegendDay
from Utils.general import create_superscript
from Utils.Clash.other import gen_season_date, gen_legend_date
from Utils.cdn import general_upload_to_cdn
from Utils.constants import POSTER_LIST, HERO_EQUIPMENT
from PIL import Image, ImageDraw, ImageFont
from coc import utils, enums, Clan
from pytz import utc
from datetime import datetime
from typing import List


async def legend_day_overview(bot: CustomClient, player: LegendPlayer, embed_color: disnake.Color):
    legend_day = player.get_legend_day()

    embed = disnake.Embed(
        description=f"**Legends Overview** | [profile]({player.share_link})\n" +
                    f"Start: {bot.emoji.legends_shield} {player.trophy_start} | Now: {bot.emoji.legends_shield} {player._.trophies}\n" +
                    f"- {legend_day.num_attacks} attacks for +{legend_day.attack_sum} trophies\n" +
                    f"- {legend_day.num_defenses} defenses for -{legend_day.defense_sum} trophies\n"
                    f"- Net: {legend_day.net_gain} trophies\n- Streak: {player.streak} triples",
        color=embed_color)

    global_ranking_text = player.ranking.global_ranking
    if isinstance(global_ranking_text, int):
        lowest_rank = await bot.legend_rankings.find({}).sort([("rank", -1)]).limit(1).to_list(length=1)
        lowest_rank = lowest_rank[0].get("rank")
        curr_rank = player.ranking.global_ranking
        if player.ranking.global_ranking < 100:
            curr_rank = 100
        mid_calc = (curr_rank / lowest_rank) * 100
        perc_of_total = round(mid_calc, 2 if mid_calc < 1 else None)
        global_ranking_text = f"{player.ranking.global_ranking} (Top {perc_of_total}%)"

    embed.add_field(name="**Rankings**",
                    value=f"- {bot.emoji.earth} {global_ranking_text} | {player.ranking.flag} {player.ranking.local_ranking}\n- Country: {player.ranking.country}",
                    inline=False)


    embed.set_author(name=f"{player._.name} | {player.clan_name}", icon_url=player.clan_badge)
    embed.set_thumbnail(url=player.townhall.image_url)

    off = ""
    gears_used = set()
    for hit in legend_day.attacks:
        if hit.timestamp is None:
            off += f"{bot.emoji.sword} +{hit.change}\n"
        else:
            for gear in hit.hero_gear:
                gears_used.add(gear)
            off += f"{bot.emoji.sword} +{hit.change} {bot.timestamper(hit.timestamp).relative}\n"

    gear_text = ""

    for hero in enums.HOME_BASE_HERO_ORDER:
        emoji_text = ""
        for gear in gears_used:
            gear_hero = HERO_EQUIPMENT.get(gear.name)
            if gear_hero == hero:
                emoji_text += f"{bot.fetch_emoji(gear.name)}{create_superscript(gear.level)}"
        if emoji_text != "":
            gear_text += f"{bot.fetch_emoji(name=hero)} | {emoji_text}\n"


    defi = ""
    for d in legend_day.defenses:
        defi += f"{bot.emoji.shield.emoji_string} -{d.change} {bot.timestamper(d.timestamp).relative}\n"

    if off == "":
        off = "No Attacks Yet."
    if defi == "":
        defi = "No Defenses Yet."
    if not gear_text:
        gear_text = "No Equipment Used"
    embed.add_field(name="**Offense**", value=off, inline=True)
    embed.add_field(name="**Defense**", value=defi, inline=True)
    embed.add_field(name="**Hero Equipment Used**", value=gear_text, inline=False)
    embed.set_footer(text=player.tag)

    link = await legend_poster(player=player)
    embed.set_image(url=link)

    return embed


async def legend_season_overview(player: LegendPlayer, embed_color: disnake.Color):

    season_stats = player.get_legend_season()
    text = f"**Attacks Won:** {player._.attack_wins} | **Def Won:** {player._.defense_wins}\n"

    start = utils.get_season_start().replace(tzinfo=utc).date()
    now = datetime.now(tz=utc).date()
    now_ = datetime.now(tz=utc)
    current_season_progress = now - start
    current_season_progress = current_season_progress.days
    if now_.hour < 5:
        current_season_progress -= 1

    day = 0
    text += f"```Day     Off  Def  Trophy\n"
    for legend_day in season_stats.values(): #type: LegendDay
        day += 1
        day_text = f"Day {day:<2}"
        trophy_finish = ""
        if legend_day.finished_trophies is not None:
            trophy_finish = f" {legend_day.finished_trophies:<4}"
        attack_text = f"{legend_day.attack_sum}{legend_day.num_attacks.superscript}"
        defense_text = f"{legend_day.defense_sum}{legend_day.num_defenses.superscript}"
        text += f"{day_text}  {attack_text:<4} {defense_text:<4}{trophy_finish}\n"
        if day == current_season_progress:
            break

    if day == 0:
        text += "\n**No Previous Days Tracked**"
    text += "```"

    embed = disnake.Embed(title=f"Season Legends Overview", description=text, color=embed_color)

    embed.set_author(name=f"{player._.name} | {player.clan_name}", icon_url=player.clan_badge, url=player.share_link)
    embed.set_thumbnail(url=player.townhall.image_url)

    month = start.month
    month = month if month != 12 else 0
    month = calendar.month_name[month + 1]
    embed.set_footer(text=f"{month} {start.year} Season")

    return embed


async def legend_poster(player: LegendPlayer, background: str =None):
    start = utils.get_season_start().replace(tzinfo=utc).date()
    today = datetime.now(tz=utc).date()
    length = today - start
    month = start.month
    if month == 12:
        month = 0
    month = calendar.month_name[month + 1]
    trophies = player._.trophies
    season = gen_season_date()

    season_stats = player.get_legend_season(season=season)
    season_stats = list(season_stats.values())
    season_stats = season_stats[0:length.days + 1]

    y = [5000] + [legend_day.finished_trophies for legend_day in reversed(season_stats) if legend_day.finished_trophies is not None]
    x = [spot for spot in range(0, len(y))]

    fig = plt.figure(dpi=100)
    ax = plt.subplot()
    ax.plot(x, y, color='white', linestyle='dashed', linewidth=3,
            marker="*", markerfacecolor="white", markeredgecolor="yellow", markersize=20)
    plt.ylim(min(y) - 25, max(y) + 100)

    plt.xlim(left=0, right=len(season_stats))
    plt.xlabel('Day', color="yellow", fontsize=14)

    plt.locator_params(axis="both", integer=True, tight=True)
    plt.gca().spines["top"].set_color("yellow")
    plt.gca().spines["bottom"].set_color("yellow")
    plt.gca().spines["left"].set_color("yellow")
    plt.gca().spines["right"].set_color("yellow")
    plt.gca().tick_params(axis='x', colors='yellow')
    plt.gca().tick_params(axis='y', colors='yellow')


    plt.ylabel('Trophies', color="yellow", fontsize=14)
    fig.savefig("Assets/poster_graph.png", transparent=True)
    plt.close(fig)

    graph = Image.open("Assets/poster_graph.png")
    if background is None:
        poster = Image.open(f"Assets/backgrounds/{random.choice(list(POSTER_LIST.values()))}.png")
    else:
        poster = Image.open(f"Assets/backgrounds/{random.choice(list(POSTER_LIST.get(background)))}.png")


    poster.paste(graph, (1175, 475), graph.convert("RGBA"))

    font = ImageFont.truetype("Assets/fonts/code.ttf", 80)
    font2 = ImageFont.truetype("Assets/fonts/blogger.ttf", 35)
    font3 = ImageFont.truetype("Assets/fonts/blogger.ttf", 60)
    font4 = ImageFont.truetype("Assets/fonts/blogger.ttf", 37)
    font5 = ImageFont.truetype("Assets/fonts/blogger.ttf", 20)
    font6 = ImageFont.truetype("Assets/fonts/blogger.ttf", 40)

    # add clan badge & text
    if player._.clan is not None:
        # clan = await player.get_detailed_clan()
        async def fetch(url, session):
            async with session.get(url) as response:
                image_data = io.BytesIO(await response.read())
                return image_data

        tasks = []
        async with aiohttp.ClientSession() as session:
            tasks.append(fetch(player._.clan.badge.large, session))
            responses = await asyncio.gather(*tasks)
            await session.close()
        badge = Image.open(responses[0])
        size = 275, 275
        badge.thumbnail(size, Image.ANTIALIAS)
        A = badge.getchannel('A')
        newA = A.point(lambda i: 128 if i > 0 else 0)
        badge.putalpha(newA)
        poster.paste(badge, (1350, 110), badge.convert("RGBA"))

        watermark = Image.new("RGBA", poster.size)
        waterdraw = ImageDraw.ImageDraw(watermark, "RGBA")
        waterdraw.text((1488, 70), player._.clan.name, anchor="mm", font=font)
        watermask = watermark.convert("L").point(lambda x: min(x, 100))
        watermark.putalpha(watermask)
        poster.paste(watermark, None, watermark)

    stats = player.get_legend_season_stats()

    draw = ImageDraw.Draw(poster)
    draw.text((585, 95), emoji.replace_emoji(player._.name, " "), anchor="mm", fill=(255, 255, 255), font=font)
    draw.text((570, 175), f"Stats collected from {len(y)} days of data", anchor="mm", fill=(255, 255, 255),font=font5)
    draw.text((360, 275), f"+{stats.average_offense} CUPS A DAY", anchor="mm", fill=(255, 255, 255), font=font2)
    draw.text((800, 275), f"-{stats.average_defense} CUPS A DAY", anchor="mm", fill=(255, 255, 255), font=font2)
    draw.text((570, 400), f"{stats.net} CUPS A DAY", anchor="mm", fill=(255, 255, 255), font=font2)
    draw.text((1240, 400), f"{trophies} | {month} {start.year}", fill=(255, 255, 255), font=font3)
    draw.text((295, 670), f"{stats.offensive_one_star}%", anchor="mm", fill=(255, 255, 255), font=font4)
    draw.text((295, 790), f"{stats.offensive_two_star}%", anchor="mm", fill=(255, 255, 255), font=font4)
    draw.text((295, 910), f"{stats.offensive_three_star}%", anchor="mm", fill=(255, 255, 255), font=font4)

    draw.text((840, 670), f"{stats.defensive_one_star}%", anchor="mm", fill=(255, 255, 255), font=font4)
    draw.text((840, 790), f"{stats.defensive_two_star}%", anchor="mm", fill=(255, 255, 255), font=font4)
    draw.text((840, 910), f"{stats.defensive_three_star}%", anchor="mm", fill=(255, 255, 255), font=font4)
    # draw.text((75, 1020), f"{month} {start.year} Season", fill=(255, 255, 255), font=font4)

    if isinstance(player.ranking.global_ranking, int):
        try:
            globe = Image.open("Assets/country_flags/globe2.png")
        except Exception:
            globe = Image.open("Assets/country_flags/globe.png")
            size = 75, 75
            globe.thumbnail(size, Image.ANTIALIAS)
            globe.save("Assets/country_flags/globe2.png", "PNG")
            globe = Image.open("Assets/country_flags/globe2.png")
        poster.paste(globe, (90, 340), globe.convert("RGBA"))
        draw.text((165, 360), f"#{player.ranking.global_ranking}", fill=(255, 255, 255), font=font6)

    if player.ranking.country_code is not None:
        try:
            globe = Image.open(f"Assets/country_flags/{player.ranking.country_code.lower()}2.png")
        except Exception:
            globe = Image.open(f"Assets/country_flags/{player.ranking.country_code.lower()}.png")
            size = 80, 80
            globe.thumbnail(size, Image.ANTIALIAS)
            globe.save(f"Assets/country_flags/{player.ranking.country_code.lower()}2.png", "PNG")
            globe = Image.open(f"Assets/country_flags/{player.ranking.country_code.lower()}2.png")

        poster.paste(globe, (770, 350), globe.convert("RGBA"))
        if isinstance(player.ranking.local_ranking, int):
            draw.text((870, 358), f"#{player.ranking.local_ranking}", fill=(255, 255, 255), font=font6)
        else:
            draw.text((870, 358), f"{player.ranking.country}", fill=(255, 255, 255), font=font6)


    # poster.show()
    temp = io.BytesIO()
    poster = poster.resize((960, 540))
    poster.save(temp, format="png", compress_level=1)
    temp.seek(0)
    link = await general_upload_to_cdn(bytes_=temp.read(), id=f"legend_poster_{player.tag.strip('#')}")

    return link


async def legend_history(bot: CustomClient, player: LegendPlayer, embed_color: disnake.Color):
    results = await bot.history_db.find({"tag": player.tag}).sort("season", -1).to_list(length=None)
    if not results:
        embed = disnake.Embed(description=f"{player._.name} has never finished a season in legends",color=disnake.Color.red())
        return embed

    names = set()
    for result in results:
        names.add(result.get("name"))
    names = list(names)

    text = ""
    oldyear = "2015"
    embed = disnake.Embed(description="🏆= trophies, 🌎= global rank", color=embed_color)
    if names:
        names = ", ".join(names)
        embed.add_field(name="**Previous Names**", value=names, inline=False)
    for result in results:
        season = result.get("season")
        year = season.split("-")[0]
        month = season.split("-")[-1]
        month = calendar.month_name[int(month)]
        month = month.ljust(9)
        month = f"`{month}`"

        year = year[0:4]
        rank = result.get("rank")
        trophies = result.get("trophies")
        if year != oldyear:
            if text != "":
                embed.add_field(name=f"**{oldyear}**", value=text, inline=False)
            oldyear = year
            text = ""
        text += f"{month} | 🏆{trophies} | 🌎{rank}\n"

    if text != "":
        embed.add_field(name=f"**{oldyear}**", value=text, inline=False)
    embed.set_author(name=f"{player._.name} Legend History", icon_url=player.townhall.image_url)
    return embed


async def legend_clan(players: List[LegendPlayer], clan: Clan, embed_color: disnake.Color):
    players.sort(key=lambda x: x._.trophies, reverse=True)
    text = f"```#  Trph Off  Def  Name\n"

    for count, player in enumerate(players, 1):
        legend_day = player.get_legend_day()
        attack_text = f"{legend_day.attack_sum}{legend_day.num_attacks.superscript}"
        defense_text = f"{legend_day.defense_sum}{legend_day.num_defenses.superscript}"
        text += f"{count:<2} {player._.trophies} {attack_text:<4} {defense_text:<4} {player.clear_name[:13]}\n"
    text += "```"

    embed = disnake.Embed(description=text, color=embed_color)
    embed.set_author(name=f"{clan.name} Legends Overview", icon_url=clan.badge.url)
    embed.set_footer(text=gen_legend_date())
    return embed
