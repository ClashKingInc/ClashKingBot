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
from utils.constants import SHORT_PLAYER_LINK

if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
else:
    cog_class = commands.Cog

class BoardCreator(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def donation_board(self, players: List[MyCustomPlayer], season: str, footer_icon: str, title_name: str, type: str, limit:int = 50,
                             embed_color: disnake.Color = disnake.Color.green()) -> disnake.Embed:
        if type == "donations":
            players.sort(key=lambda x: x.donos(date=season).donated, reverse=True)
        elif type == "received":
            players.sort(key=lambda x: x.donos(date=season).received, reverse=True)

        if type == "donations":
            text = "`  # DON     REC     NAME       `\n"
        else:
            text = "`  # REC     DON     NAME       `\n"

        total_donated = 0
        total_received = 0
        for count, player in enumerate(players, 1):
            tag = player.tag.strip("#")
            if count <= limit:
                if type == "donations":
                    text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {player.donos(date=season).donated:5} {player.donos(date=season).received:5} {player.clear_name[:13]:13}`\n"
                else:
                    text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {player.donos(date=season).received:5} {player.donos(date=season).donated:5} {player.clear_name[:13]:13}`\n"

            total_donated += player.donos(date=season).donated
            total_received += player.donos(date=season).received

        embed = disnake.Embed(description=f"{text}", color=embed_color)
        embed.set_author(name=f"{title_name} Top {min(limit, len(players))} {type.capitalize()}", icon_url=self.bot.emoji.clan_castle.partial_emoji.url)
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
        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        return (await board_cog.graph_creator(df=df, x="Date", y="Total Activity", title=title))

    async def capital_donation_board(self, players: List[MyCustomPlayer], week: str, title_name: str, limit: int = 60, footer_icon: str = None, embed_color: disnake.Color = disnake.Color.green()):
        players.sort(key=lambda x: sum(x.clan_capital_stats(week=week).donated), reverse=True)
        total_donated = 0
        text = ""
        for count, player in enumerate(players, 1):
            tag = player.tag.strip("#")
            if count <= limit:
                text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {sum(player.clan_capital_stats(week=week).donated):5} {player.clear_name[:13]:13}`\n"
            total_donated += sum(player.clan_capital_stats(week=week).donated)
        if text == "":
            text = "No Results Found"
        embed = disnake.Embed(description=f"{text}", color=embed_color)
        embed.set_author(name=f"{title_name} Clan Capital Donations", icon_url=self.bot.emoji.capital_gold.partial_emoji.url)
        if footer_icon is None:
            footer_icon = self.bot.user.avatar.url
        embed.set_footer(icon_url=footer_icon, text=f"Donated: {'{:,}'.format(total_donated)} | {week}")
        embed.timestamp = datetime.datetime.now()
        return embed

    async def capital_raided_board(self, players: List[MyCustomPlayer], week: str, title_name: str, limit: int = 60, footer_icon: str = None, embed_color: disnake.Color = disnake.Color.green()):
        players.sort(key=lambda x: sum(x.clan_capital_stats(week=week).raided), reverse=True)
        total_donated = 0
        text = ""
        for count, player in enumerate(players, 1):
            tag = player.tag.strip("#")
            if count <= limit:
                text += f"[⌕]({SHORT_PLAYER_LINK}{tag})`{count:2} {sum(player.clan_capital_stats(week=week).raided):5} {player.clear_name[:13]:13}`\n"
            total_donated += sum(player.clan_capital_stats(week=week).raided)
        if text == "":
            text = "No Results Found"
        embed = disnake.Embed(description=f"{text}", color=embed_color)
        embed.set_author(name=f"{title_name} Clan Capital Raid Totals", icon_url=self.bot.emoji.capital_gold.partial_emoji.url)
        if footer_icon is None:
            footer_icon = self.bot.user.avatar.url
        embed.set_footer(icon_url=footer_icon, text=f"Raided: {'{:,}'.format(total_donated)} | {week}")
        embed.timestamp = datetime.datetime.now()
        return embed