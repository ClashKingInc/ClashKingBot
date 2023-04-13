import pytz
from disnake.ext import commands
import disnake
from typing import List, TYPE_CHECKING
import coc
import datetime
import datetime as dt
import pandas as pd

from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from collections import defaultdict
from utils.constants import CK_API_ROUTE

if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
else:
    cog_class = commands.Cog

class BoardCreator(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def donation_board(self, players: List[MyCustomPlayer], season: str, footer_icon: str, title_name: str, type: str,
                             embed_color: disnake.Color = disnake.Color.green()) -> disnake.Embed:

        look_type = "donations"
        if type == "received":
            look_type = "donationsReceived"
        pipeline = [{"$match" : {"$and" : [
                    {"tag" : {"$in" : [player.tag for player in players]}},
                    {"type" : look_type},
                    ]}},
                    { "$sort": {"tag": 1, "time": -1} },
                    { "$group": {
                        "_id": "$tag",
                        "matched_doc": { "$first": "$$ROOT" }
                    }} ]
        history_results = await self.bot.player_history.aggregate(pipeline).to_list(length=None)
        history_result_dict = {}
        for result in history_results:
            history_result_dict[result.get("_id")] = result.get("matched_doc").get("time")

        if type == "donations":
            players.sort(key=lambda x: x.donos(date=season).donated, reverse=True)
        elif type == "received":
            players.sort(key=lambda x: x.donos(date=season).received, reverse=True)

        if type == "donations":
            text = "`  # DON     LT NAME       `\n"
        else:
            text = "`  # REC     LT NAME       `\n"

        total_donated = 0
        total_received = 0
        for count, player in enumerate(players, 1):
            tag = player.tag.strip("#")
            if count <= 50:
                last_date = history_result_dict.get(player.tag)
                if last_date is not None:
                    last_date = datetime.datetime.fromtimestamp(last_date)
                    diff = (datetime.datetime.now() - last_date)
                    days = int(diff.days)
                    hours = int(diff.total_seconds()//3600)
                    mins = int((diff.total_seconds()//60)%60)
                    if days != 0:
                        last_date = f"{days:>2}d"
                    elif hours != 0:
                        last_date = f"{hours:>2}h"
                    else:
                        last_date = f"{mins:>2}m"
                else:
                    last_date = "30d"
                if type == "donations":
                    text += f"[⌕]({CK_API_ROUTE}{tag})`{count:2} {player.donos(date=season).donated:5} {last_date} {player.name[:13]:13}`\n"
                else:
                    text += f"[⌕]({CK_API_ROUTE}{tag})`{count:2} {player.donos(date=season).received:5} {last_date} {player.name[:13]:13}`\n"

            total_donated += player.donos(date=season).donated
            total_received += player.donos(date=season).received

        embed = disnake.Embed(title=f"**{title_name} Top {len(players)} {type.capitalize()}**", description=f"{text}", color=embed_color)
        if footer_icon is None:
            footer_icon = self.bot.user.avatar.url
        embed.set_footer(icon_url=footer_icon, text=f"Donations: {'{:,}'.format(total_donated)} | Received : {'{:,}'.format(total_received)} | {season}")
        embed.timestamp = datetime.datetime.now()
        return embed

    async def activity_board(self, players: List[MyCustomPlayer], season: str, footer_icon: str, title_name: str, embed_color: disnake.Color = disnake.Color.green()) -> disnake.Embed:
        players.sort(key=lambda x: len(x.season_last_online(season_date=season)), reverse=True)
        text = "`#  ACT   NAME      `\n"
        total_activities = 0
        for count, player in enumerate(players, 1):
            if count <= 50:
                text += f"{self.bot.get_number_emoji(color='gold', number=count)}`{len(player.season_last_online(season_date=season)):4} {player.name[:15]:15}`\n"
            total_activities += len(player.season_last_online(season_date=season))

        embed = disnake.Embed(title=f"**{title_name} Top {len(players)} Activities**", description=f"{text}",color=embed_color)
        if footer_icon is None:
            footer_icon = self.bot.user.avatar.url
        embed.set_footer(icon_url=footer_icon, text=f"Activities: {'{:,}'.format(total_activities)} | {season}")
        embed.timestamp = datetime.datetime.now()
        return embed

    async def activity_graph(self, players: List[MyCustomPlayer], season: str, title: str, granularity: str, time_zone: str) -> (disnake.File, disnake.ActionRow):
        list_ = []
        days = defaultdict(int)
        for player in players:
            all_lo = player.season_last_online(season_date=season)
            for time in all_lo:
                if granularity == "Day":
                    time = dt.datetime.fromtimestamp(time).replace(hour=0, minute=0, second=0)
                elif granularity == "Hour":
                    time = dt.datetime.fromtimestamp(time).replace(minute=0, second=0)
                elif granularity == "Quarter-Day":
                    time = dt.datetime.fromtimestamp(time)
                    time = time.replace(hour=(time.hour // 6) * 6, minute=0, second=0)
                if player.clan is None:
                    continue
                days[f"{int(time.timestamp())}_{player.clan.name}"] += 1
        for date_time, amount in days.items():
            list_.append([pd.to_datetime(int(date_time.split("_")[0]), unit="s", utc=True).tz_convert(time_zone), amount, date_time.split("_")[1]])
        df = pd.DataFrame(list_, columns=["Date", "Total Activity", "Clan"])
        df.sort_values(by="Date", inplace=True)
        print(df)
        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        return (await board_cog.graph_creator(df=df, x="Date", y="Total Activity", title=title))




