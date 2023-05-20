import coc
from disnake.ext import commands
import disnake
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
import io
import pandas as pd
import datetime as dt
from collections import defaultdict, Counter
from typing import TYPE_CHECKING, List
from utils.General import create_superscript
from urllib.request import Request
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import urllib.parse

if TYPE_CHECKING:
    from Graphing import GraphCog
    graphcog = GraphCog.GraphCog
else:
    graphcog = commands.Cog

LEAGUES = ["Legend League", "Titan League I" , "Titan League II" , "Titan League III" ,"Champion League I", "Champion League II", "Champion League III",
                   "Master League I", "Master League II", "Master League III",
                   "Crystal League I","Crystal League II", "Crystal League III",
                   "Gold League I","Gold League II", "Gold League III",
                   "Silver League I","Silver League II","Silver League III",
                   "Bronze League I", "Bronze League II", "Bronze League III", "Unranked"]

class DataWrapperGraphs(graphcog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def create_clan_donation_graph(self, server_id: int, all_players: List[MyCustomPlayer], clans:List[coc.Clan], season: str, type: str):
        clan_tags = set([clan.tag for clan in clans])
        dono_dict = defaultdict(int)
        rec_dict = defaultdict(int)
        clan_tag_to_name = {}
        for member in all_players:
            if member.clan is not None and member.clan.tag in clan_tags:
                dono_dict[member.clan.tag] += member.donos(date=season).donated
                rec_dict[member.clan.tag] += member.donos(date=season).received
                clan_tag_to_name[member.clan.tag] = member.clan.name

        list_ = []
        num = defaultdict(int)
        for tag, name in clan_tag_to_name.items():
            if dono_dict.get(tag, 0) == 0 and rec_dict.get(tag, 0) == 0:
                continue
            num[name] += 1
            if num[name] >= 2:
                list_.append([f"{name}{create_superscript(num[name])}", dono_dict.get(tag, 0), rec_dict.get(tag, 0)])
            else:
                list_.append([f"{name}", dono_dict.get(tag, 0), rec_dict.get(tag, 0)])

        df = pd.DataFrame(list_, columns=["Clan", "Donations", "Received"])
        if type == "donations":
            df.sort_values(ascending=False, by="Donations", inplace=True)
        elif type == "received":
            df.sort_values(ascending=False,by="Received", inplace=True)

        metadata = {"describe" : {"byline" : "Created by ClashKing"}}
        '''
        chart_info = self.bot.data_wrapper.create_chart(title="Clan Donations", chart_type="d3-bars-split", data=df, metadata=metadata)
        self.bot.data_wrapper.publish_chart(chart_id=chart_info.get("id"), display=False)
        return f"https://datawrapper.dwcdn.net/{chart_info['id']}/full.png"'''

        return (await self.create_and_publish_chart(server_id=server_id, title="Clan Donations", chart_type="d3-bars-split", data=df, metadata=metadata, gtype="donos", season=season))



