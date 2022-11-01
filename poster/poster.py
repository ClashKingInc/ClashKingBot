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

class Poster(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def autocomp_names(self, user_input: str):
        results = await self.bot.search_name_with_tag(query=user_input, poster=True)
        return results

    @commands.slash_command(name="poster", description="Poster w/ graph & stats to show off season legends stats")
    async def create_poster(self, ctx, smart_search: str = commands.Param(autocomplete=autocomp_names),
                           background: str = commands.Param(default=None,
        choices=["Edrag", "Hogrider", "Clash Forest", "Clan War", "Loons", "Witch", "Archers", "Bowler", "Barbs", "Barb & Archer", "Big Boy Skelly",
                 "Wiz Tower", "Spells", "Barb Sunset", "Wood Board", "Clash Sky", "Super Wizard", "Village Battle", "Hero Pets"]),
                previous_season:str = commands.Param(default=None, choices=["Yes"])):
        """
            Parameters
            ----------
            smart_search: Name or player tag to search with
            background: Which background for poster to use (optional)
            previous_season: (optional)
        """

        await ctx.response.defer()

        if utils.is_valid_tag(smart_search) is False:
            if "|" not in smart_search:
                embed = disnake.Embed(
                    description="Not a valid player tag, make sure to choose an option from the autocomplete",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)


        player: MyCustomPlayer = await self.bot.getPlayer(player_tag=smart_search, custom=True)
        if player is None:
            embed = disnake.Embed(
                description="Not a valid player tag.",
                color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)


        if previous_season == "Yes":
            # current season start date
            # use to get previous season (month - 1)
            # end of last season is beginning of current
            end = utils.get_season_start().replace(tzinfo=utc).date()
            start = utils.get_season_start(month=end.month - 1, year=end.year).replace(tzinfo=utc).date()
            month = calendar.month_name[start.month + 1]
            try:
                id = player.legend_statistics.previous_season.id
                mon = start.month
                if mon <= 9:
                    mon = f"0{mon}"
                season = f"{start.year}-{mon}"
                if str(id) != f"{start.year}-{mon}":
                    embed = disnake.Embed(
                        description="No statistics for last season (if new season just started allow api time to add new season data)",
                        color=disnake.Color.red())
                    return await ctx.edit_original_message(embed=embed)
            except:
                embed = disnake.Embed(
                    description="Player was not in legends last season",
                    color=disnake.Color.red())
                return await ctx.edit_original_message(embed=embed)

            trophies = player.legend_statistics.previous_season.trophies

        else:
            start = utils.get_season_start().replace(tzinfo=utc).date()
            today = datetime.utcnow().date()
            length = today-start
            month = calendar.month_name[start.month + 1]
            trophies = player.trophies
            season = self.bot.gen_season_date()

        season_stats = player.season_of_legends(season=season)
        season_stats = list(season_stats.values())
        if previous_season != "Yes":
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

        if previous_season != "Yes":
            plt.xlim(int(len(season_stats)), -1)
            plt.xlabel('Days Ago', color="yellow", fontsize=14)
        else:
            plt.xticks([], [])
            plt.xlabel('Trophies Over Time', color="yellow", fontsize=14)

        plt.gca().spines["top"].set_color("yellow")
        plt.gca().spines["bottom"].set_color("yellow")
        plt.gca().spines["left"].set_color("yellow")
        plt.gca().spines["right"].set_color("yellow")
        plt.gca().tick_params(axis='x', colors='yellow')
        plt.gca().tick_params(axis='y', colors='yellow')

        # naming the x axis

        # naming the y axis
        plt.ylabel('Trophies', color="yellow", fontsize=14)
        #encoded_string = name.encode("ascii", "ignore")
        #decode_string = encoded_string.decode()
        plt.savefig("poster/poster_graph.png", transparent=True)
        plt.clf()
        plt.close("all")

        graph = Image.open("poster/poster_graph.png")
        if background is None:
            poster = Image.open(f"poster/backgrounds/{random.choice(list(POSTER_LIST.values()))}.png")
        else:
            poster = Image.open(f"poster/backgrounds/{POSTER_LIST.get(background)}.png")

        gspot = None
        flag = None
        cou_spot = None
        if previous_season != "Yes":
            pass
        else:
            try:
                gspot = player.legend_statistics.previous_season.rank
            except:
                gspot = None

            if gspot is not None and gspot > 99999:
                gspot = None

        poster.paste(graph, (1175, 475), graph.convert("RGBA"))

        font = ImageFont.truetype("poster/fonts/code.TTF", 80)
        font2 = ImageFont.truetype("poster/fonts/blogger.ttf", 35)
        font3 = ImageFont.truetype("poster/fonts/blogger.ttf", 60)
        font4 = ImageFont.truetype("poster/fonts/blogger.ttf",37)
        font5 = ImageFont.truetype("poster/fonts/blogger.ttf", 20)
        font6 = ImageFont.truetype("poster/fonts/blogger.ttf", 40)

        #add clan badge & text
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
        draw.text((585, 95), player.name, anchor="mm", fill=(255,255,255), font=font)
        draw.text((570, 175), f"Stats collected from {len(y)} days of data", anchor="mm", fill=(255, 255, 255), font=font5)

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
        #draw.text((75, 1020), f"{month} {start.year} Season", fill=(255, 255, 255), font=font4)

        if gspot is not None:
            globe = Image.open("poster/globe.png")
            size = 75,75
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

        #poster.show()
        temp = io.BytesIO()
        poster.save(temp, format="png")
        temp.seek(0)
        file = disnake.File(fp=temp, filename="filename.png")

        await ctx.edit_original_message(file=file)



