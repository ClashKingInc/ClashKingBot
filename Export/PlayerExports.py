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

class PlayerExportCreator(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot


