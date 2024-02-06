import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from classes.bot import CustomClient
else:
    from disnake.ext.commands import AutoShardedBot as CustomClient
import coc
import plotly.express as px
import plotly.io as pio
import io
import pandas as pd
import datetime as dt
import plotly.graph_objects as go

from collections import defaultdict, Counter
from typing import List
from utils.general import create_superscript
from classes.player import MyCustomPlayer


async def create_clan_donation_graph(bot: CustomClient, clans: List[coc.Clan], townhalls: List[int], season: str, type: str):
    pipeline = [
        {"$match": {"$and": [{"clan_tag": {"$in": [clan.tag for clan in clans]}}, {"townhall": {"$in": townhalls}}]}},
        {"$group": {"_id": "$clan_tag", "total_donated": {"$sum": f"$donations.{season}.donated"},
                    "total_received": {"$sum": f"$donations.{season}.received"}}},
        {"$sort": {f"total_{type}": 1}}
    ]
    results = await bot.player_stats.aggregate(pipeline).to_list(length=None)
    clan_tags = set([clan.tag for clan in clans])
    x = []
    y = []
    text = []
    sums = {"total_donated": sum([x["total_donated"] for x in results]),
            "total_received": sum([x["total_received"] for x in results])}
    names_plotted = defaultdict(int)
    nums_zero = 0
    for result in results:
        if result["_id"] in clan_tags:
            perc = int((result[f'total_{type}'] / sums[f"total_{type}"]) * 100)
            if perc == 0:
                nums_zero += 1
                if nums_zero > 5 or len(clan_tags) >= 15:
                    continue
            x.append(result[f'total_{type}'])
            name = f"{coc.utils.get(clans, tag=result['_id']).name}"
            if names_plotted[name] > 0:
                y.append(f"{name}{create_superscript(names_plotted[name] + 1)}")
            else:
                y.append(f"{name}")
            r = "{:,}".format(result[f'total_{type}'])
            text.append(f"{r} | {perc}%")
            names_plotted[name] += 1

    fig = go.Figure(go.Bar(
        x=x,
        y=y,
        text=text,
        textposition="inside",
        textfont=dict(color="white"),
        orientation='h'))
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    fig.update_layout(barmode="overlay", template="plotly_white", margin=dict(l=50, r=25, b=25, t=25, pad=4), width=750,
                      height=500)
    img = pio.to_image(fig, format="png", scale=3.0)
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file, sums["total_donated"], sums["total_received"]