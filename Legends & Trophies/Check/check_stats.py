
from disnake.ext import commands
import disnake
from coc import utils
from pytz import utc
from datetime import datetime
import calendar
import random
from CustomClasses.CustomPlayer import MyCustomPlayer, LegendDay
from CustomClasses.CustomBot import CustomClient
import aiohttp
import asyncio
POSTER_LIST = {"Edrag" : "edrag",
               "Hogrider" : "hogrider",
               "Clash Forest" : "clashforest",
               "Clan War" : "clanwar",
               "Loons" : "loons",
               "Witch" : "witch",
               "Archers" : "archers",
               "Bowler" : "bowler",
               "Barbs" : "barbs",
               "Barb & Archer" : "barbandarcher",
               "Big Boy Skelly" : "bigboy",
               "Wiz Tower" : "wiztower",
               "Spells" : "spells",
               "Barb Sunset" : "barbsunset",
               "Wood Board" : "woodboard",
               "Clash Sky" : "clashsky",
               "Super Wizard" : "swiz",
               "Village Battle" : "villagebattle",
               "Hero Pets" : "heropets"}

from Utils.cdn import general_upload_to_cdn
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io


class CheckStats(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def checkEmbed(self, player: MyCustomPlayer):

        if player.league_as_string != "Legend League":
            embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name()}",
                                  description=f"Player not currently in legends.",
                                  color=disnake.Color.blue())
            return embed

        legend_day = player.legend_day()
        embed = disnake.Embed(
            description=f"**Legends Overview** | [profile]({player.share_link})\n" +
                        f"Start: {self.bot.emoji.legends_shield.emoji_string} {player.trophy_start()} | Now: {self.bot.emoji.legends_shield.emoji_string} {player.trophies}\n" +
                        f"- {legend_day.num_attacks.integer} attacks for +{legend_day.attack_sum} trophies\n" +
                        f"- {legend_day.num_defenses.integer} defenses for -{legend_day.defense_sum} trophies\n"
                        f"- Net: {legend_day.net_gain} trophies\n- Streak: {player.streak} triples",
            color=disnake.Color.from_rgb(r=43, g=45, b=49))

        ranking = await player.ranking()
        embed.add_field(name="**Stats**",
                        value=f"- Rank: {self.bot.emoji.earth.emoji_string} {ranking.global_ranking} | {ranking.flag} {ranking.local_ranking}\n- Country: {ranking.country}"
                        , inline=False)


        embed.set_author(name=f"{player.name} | {player.clan_name()}", icon_url=f"{player.clan_badge_link()}")
        embed.set_thumbnail(url=player.town_hall_cls.image_url)

        off = ""
        for hit in legend_day.attacks:
            off += f"{self.bot.emoji.sword.emoji_string} +{hit}\n"

        defi = ""
        for d in legend_day.defenses:
            defi += f"{self.bot.emoji.shield.emoji_string} -{d}\n"

        if off == "":
            off = "No Attacks Yet."
        if defi == "":
            defi = "No Defenses Yet."
        embed.add_field(name="**Offense**", value=off, inline=True)
        embed.add_field(name="**Defense**", value=defi, inline=True)
        embed.set_footer(text=player.tag)

        link = await self.check_poster(player=player)
        embed.set_image(url=link)

        return embed


    async def checkYEmbed(self, player: MyCustomPlayer):

        season_stats = player.season_of_legends()

        '''
        embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name()}",
                              description=f"No previous stats for this season.",
                              color=disnake.Color.blue())
        return embed
        '''

        if player.league_as_string != "Legend League":
            embed = disnake.Embed(title=f"{player.name} ({player.tag}) | {player.clan_name()}",
                                  description=f"Player not currently in legends.",
                                  color=disnake.Color.blue())
            return embed


        text = f""
        initial = f"**Attacks Won:** {player.attack_wins} | **Def Won:** {player.defense_wins}\n"
        text += initial

        start = utils.get_season_start().replace(tzinfo=utc).date()
        now = datetime.now(tz=utc).date()
        now_ = datetime.now(tz=utc)
        current_season_progress = now - start
        current_season_progress = current_season_progress.days

        if now_.hour < 5:
            current_season_progress -= 1
        day = 0
        for legend_day in season_stats.values():
            day+=1
            legend_day: LegendDay

            day_text = f"Day {day}"
            day_text = day_text.ljust(6)
            text+=f"`{day_text}` {self.bot.emoji.sword.emoji_string}{legend_day.attack_sum}{legend_day.num_attacks.superscript} " \
                  f"{self.bot.emoji.shield.emoji_string}{legend_day.defense_sum}{legend_day.num_defenses.superscript}\n"
            if day == current_season_progress:
                break

        if text == initial:
            text += "\n**No Previous Days Tracked**"
        embed = disnake.Embed(title=f"Season Legends Overview",
                              description=text,
                              color=disnake.Color.from_rgb(r=43, g=45, b=49))


        embed.set_author(name=f"{player.name} | {player.clan_name()}", icon_url=f"{player.clan_badge_link()}", url=player.share_link)
        embed.set_thumbnail(url=player.town_hall_cls.image_url)

        month = start.month
        if month == 12:
            month = 0
        month = calendar.month_name[month + 1]
        embed.set_footer(text=f"{month} {start.year} Season")

        return embed


    async def check_poster(self, player: MyCustomPlayer):
        start = utils.get_season_start().replace(tzinfo=utc).date()
        today = datetime.utcnow().date()
        length = today - start
        month = start.month
        if month == 12:
            month = 0
        month = calendar.month_name[month + 1]
        trophies = player.trophies
        season = self.bot.gen_season_date()

        season_stats = player.season_of_legends(season=season)
        season_stats = list(season_stats.values())
        season_stats = season_stats[0:length.days + 1]

        y = []
        new_trophies = trophies
        for legend_day in reversed(season_stats):
            net = legend_day.net_gain
            new_trophies -= net
            y.append(new_trophies)

        x = []
        for spot in range(0, len(season_stats)):
            x.append(spot)

        fig = plt.figure(dpi=100)
        ax = plt.subplot()
        ax.plot(x, y, color='white', linestyle='dashed', linewidth=3,
                marker="*", markerfacecolor="white", markeredgecolor="yellow", markersize=20)
        plt.ylim(min(y) - 100, max(y) + 100)

        plt.xlim(int(len(season_stats)), -1)
        plt.xlabel('Days Ago', color="yellow", fontsize=14)

        plt.gca().spines["top"].set_color("yellow")
        plt.gca().spines["bottom"].set_color("yellow")
        plt.gca().spines["left"].set_color("yellow")
        plt.gca().spines["right"].set_color("yellow")
        plt.gca().tick_params(axis='x', colors='yellow')
        plt.gca().tick_params(axis='y', colors='yellow')

        # naming the x axis

        # naming the y axis
        plt.ylabel('Trophies', color="yellow", fontsize=14)
        # encoded_string = name.encode("ascii", "ignore")
        # decode_string = encoded_string.decode()
        fig.savefig("poster/poster_graph.png", transparent=True)
        plt.close(fig)

        graph = Image.open("poster/poster_graph.png")

        poster = Image.open(f"poster/backgrounds/{random.choice(list(POSTER_LIST.values()))}.png")

        gspot = None
        flag = None
        cou_spot = None

        poster.paste(graph, (1175, 475), graph.convert("RGBA"))

        font = ImageFont.truetype("poster/fonts/code.ttf", 80)
        font2 = ImageFont.truetype("poster/fonts/blogger.ttf", 35)
        font3 = ImageFont.truetype("poster/fonts/blogger.ttf", 60)
        font4 = ImageFont.truetype("poster/fonts/blogger.ttf", 37)
        font5 = ImageFont.truetype("poster/fonts/blogger.ttf", 20)
        font6 = ImageFont.truetype("poster/fonts/blogger.ttf", 40)

        # add clan badge & text
        if player.clan is not None:
            # clan = await player.get_detailed_clan()
            async def fetch(url, session):
                async with session.get(url) as response:
                    image_data = io.BytesIO(await response.read())
                    return image_data

            tasks = []
            async with aiohttp.ClientSession() as session:
                tasks.append(fetch(player.clan.badge.large, session))
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
            waterdraw.text((1488, 70), player.clan.name, anchor="mm", font=font)
            watermask = watermark.convert("L").point(lambda x: min(x, 100))
            watermark.putalpha(watermask)
            poster.paste(watermark, None, watermark)

        stats = player.season_legend_stats()

        draw = ImageDraw.Draw(poster)
        draw.text((585, 95), player.name, anchor="mm", fill=(255, 255, 255), font=font)
        draw.text((570, 175), f"Stats collected from {len(y)} days of data", anchor="mm", fill=(255, 255, 255),
                  font=font5)

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

        if gspot is not None:
            globe = Image.open("poster/globe.png")
            size = 75, 75
            globe.thumbnail(size, Image.ANTIALIAS)
            globe.save("poster/globe2.png", "PNG")
            globe = Image.open("poster/globe2.png")
            poster.paste(globe, (90, 340), globe.convert("RGBA"))
            draw.text((180, 360), f"#{gspot}", fill=(255, 255, 255), font=font6)

        try:
            if flag is not None:
                globe = Image.open(f"poster/country_flags/{flag}.png")
                size = 80, 80
                globe.thumbnail(size, Image.ANTIALIAS)
                globe.save(f"poster/country_flags/{flag}2.png", "PNG")
                globe = Image.open(f"poster/country_flags/{flag}2.png")
                poster.paste(globe, (770, 350), globe.convert("RGBA"))
                draw.text((870, 355), f"#{cou_spot}", fill=(255, 255, 255), font=font6)
        except:
            pass

        # poster.show()
        temp = io.BytesIO()
        poster = poster.resize((960, 540))
        poster.save(temp, format="png", compress_level=1)
        temp.seek(0)
        link = await general_upload_to_cdn(bytes_=temp.read(), id=f"legend_poster_{player.tag.strip('#')}")

        return link

