from disnake.ext import commands
import disnake
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
from coc import utils
import pytz
utc = pytz.utc
from datetime import datetime
import calendar
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
import random
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


class CheckPoster(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def createPosterEmbed(self, player: MyCustomPlayer):

        start = utils.get_season_start().replace(tzinfo=utc).date()
        today = datetime.utcnow().date()
        length = today - start
        month = calendar.month_name[start.month + 1]
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

        plt.plot(x, y, color='white', linestyle='dashed', linewidth=3,
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
        plt.savefig("poster/poster_graph.png", transparent=True)
        plt.clf()
        plt.close("all")

        graph = Image.open("poster/poster_graph.png")

        poster = Image.open(f"poster/backgrounds/{random.choice(list(POSTER_LIST.values()))}.png")


        gspot = None
        flag = None
        cou_spot = None

        poster.paste(graph, (1175, 475), graph.convert("RGBA"))

        font = ImageFont.truetype("poster/fonts/code.TTF", 80)
        font2 = ImageFont.truetype("poster/fonts/blogger.ttf", 35)
        font3 = ImageFont.truetype("poster/fonts/blogger.ttf", 60)
        font4 = ImageFont.truetype("poster/fonts/blogger.ttf", 37)
        font5 = ImageFont.truetype("poster/fonts/blogger.ttf", 20)
        font6 = ImageFont.truetype("poster/fonts/blogger.ttf", 40)

        # add clan badge & text
        if player.clan is not None:
            clan = await player.get_detailed_clan()
            await clan.badge.save("poster/clanbadge.png", size="large")
            badge = Image.open("poster/clanbadge.png")
            size = 275, 275
            badge.thumbnail(size, Image.ANTIALIAS)
            A = badge.getchannel('A')
            newA = A.point(lambda i: 128 if i > 0 else 0)
            badge.putalpha(newA)
            poster.paste(badge, (1350, 110), badge.convert("RGBA"))

            watermark = Image.new("RGBA", poster.size)
            waterdraw = ImageDraw.ImageDraw(watermark, "RGBA")
            waterdraw.text((1488, 70), clan.name, anchor="mm", font=font)
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
        poster.save(temp, format="png")
        temp.seek(0)
        file = disnake.File(fp=temp, filename="filename.png")

        pic_channel = await self.bot.fetch_channel(884951195406458900)
        msg = await pic_channel.send(file=file)
        pic = msg.attachments[0].url

        embed = disnake.Embed(title=f"{player.name}'s Estimated Season Stats",
                              color=disnake.Color.blue())

        embed.set_image(url=pic)

        return embed