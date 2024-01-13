import disnake
import plotly.express as px
import plotly.io as pio
import io
import pandas as pd
from CustomClasses.CustomBot import CustomClient

async def graph_creator(bot: CustomClient, df: pd.DataFrame, x: str, y: str, title: str, no_html:bool = False, footer: str= None):
    fig = px.line(df, x=x, y=y, title=title, line_shape="spline", color="Clan")
    if footer is not None:
        fig.add_annotation(dict(font=dict(color='black', size=15),
                                x=.32,
                                y=-0.13,
                                showarrow=False,
                                text=footer,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))
    pio.write_html(fig, file="index.html", auto_open=False)
    img = pio.to_image(fig, format="png", scale=3.0)
    if not no_html:
        file = disnake.File(fp="index.html", filename="test.html")
        channel = await bot.getch_channel(884951195406458900)
        msg = await channel.send(file=file)
        html = msg.attachments[0].url
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="Online View", url=f"https://api.clashking.xyz/renderhtml/?url={html}"))
    else:
        buttons = None
    file = disnake.File(fp=io.BytesIO(img), filename="test.png")

    return (file, buttons)