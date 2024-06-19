import disnake
import plotly.io as pio
import io
import plotly.graph_objects as go

from collections import defaultdict
from utility.general import create_superscript


def comparison_bar_graph(full_totals: dict, clan_totals: dict):
    keys = list(clan_totals[0].keys())
    spot_key = [k for k in keys if k not in ["name", "tag"]][0]
    overall_total = full_totals.get(spot_key)
    overall_total = max(overall_total, 1)
    names_plotted = defaultdict(int)
    nums_zero = 0
    x = []
    y = []
    text = []
    for result in sorted(clan_totals, key=lambda x: x.get(spot_key)):
        perc = int((result.get(spot_key) / overall_total) * 100)
        if perc == 0:
            nums_zero += 1
            if nums_zero > 2 or len(clan_totals) >= 15:
                continue
        x.append(result.get(spot_key))
        if names_plotted[result.get("name")] > 0:
            y.append(f"{result.get('name')}{create_superscript(names_plotted[result.get('name')] + 1)}")
        else:
            y.append(f"{result.get('name')}")
        r = "{:,}".format(result.get(spot_key))
        text.append(f"{r} | {perc}%")
        names_plotted[result.get("name")] += 1
    # x = total
    # y = name
    # text = text on bar
    fig = go.Figure(
        go.Bar(
            x=x,
            y=y,
            text=text,
            textposition="inside",
            textfont=dict(color="white"),
            orientation="h",
        )
    )
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")

    fig.update_layout(
        barmode="overlay",
        template="plotly_white",
        margin=dict(l=50, r=25, b=25, t=25, pad=4),
        width=750,
        height=500,
    )
    img = pio.to_image(fig, format="png", scale=3.0)
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")
    return file
