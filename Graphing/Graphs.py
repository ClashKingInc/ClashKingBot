from disnake.ext import commands
import disnake
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
import plotly.express as px
import plotly.io as pio
import io
import pandas as pd
import datetime as dt
from collections import defaultdict, Counter
LEAGUES = ["Legend League", "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]

class GraphCreator(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    def get_closest(self, keys: list, time: int):
        previous_key = keys[0]
        for key in keys:
            if time - key < 0:
                return previous_key
            previous_key = key
        return previous_key


    @commands.slash_command(name="graph")
    async def g(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        players = self.bot.historical_stats.find({}, {"league" : 1, "trophies" : 1}).limit(100000)

        league_sample_count = defaultdict(int)
        league_heat = defaultdict(lambda: defaultdict(int))
        # league : {hour : heat}
        async for player in players:
            league = player.get("league")
            if league is None:
                continue
            league_dict = {}
            for le in league:
                league_dict[le["time"]] = le["value"]["name"]
            list_keys = list(league_dict.keys())
            for trophy in player.get("trophies", []):
                time = dt.datetime.fromtimestamp(trophy.get("time"))
                league = league_dict[self.get_closest(keys=list_keys, time=trophy.get("time"))]
                if league_sample_count[league] > 5000:
                    continue
                league_sample_count[league] += 1
                league_heat[f"{league}"][time.hour] += 1

        leagues = [league for league in LEAGUES if league in list(league_heat.keys())]
        times = list(f"{x}:00" for x in range(24))

        l = []
        for league_name in leagues:
            heat = league_heat[league_name]
            empty = [0] * 24
            for hour, num in heat.items():
                empty[hour] = num
            l.append(empty)


        '''for date_time, amount in days.items():
            list_.append(
                [pd.to_datetime(int(date_time.split("_")[0]), unit="s", utc=True).tz_convert(time_zone), amount,
                 date_time.split("_")[1]])
        df = pd.DataFrame(list_, columns=["Date", "Total Activity", "Clan"])
        df.sort_values(by="Date", inplace=True)'''



        fig = px.imshow(l,
                        labels=dict(x="Time", y="League", color="Activity"),
                        x=times,
                        y=leagues,
                        title="Activity Per Hour Per League"
                        )
        fig.update_xaxes(side="bottom")
        fig.show()
        pio.write_html(fig, file="index.html", auto_open=False)
        img = pio.to_image(fig, format="png", scale=3.0)
        file = disnake.File(fp="index.html", filename="test.html")
        channel = await self.bot.getch_channel(884951195406458900)
        msg = await channel.send(file=file)
        html = msg.attachments[0].url
        file = disnake.File(fp=io.BytesIO(img), filename="test.png")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="Online View", url=f"https://api.clashking.xyz/render/?url={html}"))
        await ctx.edit_original_message(file=file, components=[buttons])


    async def graph_creator(self, df: pd.DataFrame, x:str, y:str, title:str):
        fig = px.line(df, x=x, y=y, title=title, line_shape="spline", color="Clan")

        pio.write_html(fig, file="index.html", auto_open=False)
        img = pio.to_image(fig, format="png", scale=3.0)
        file = disnake.File(fp="index.html", filename="test.html")
        channel = await self.bot.getch_channel(884951195406458900)
        msg = await channel.send(file=file)
        html = msg.attachments[0].url
        file = disnake.File(fp=io.BytesIO(img), filename="test.png")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="Online View", url=f"https://api.clashking.xyz/render/?url={html}"))
        return(file, buttons)
