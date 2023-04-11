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


class ExportCommands(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="export")
    async def export(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @export.sub_command(name="template", description="Upload or Download a template")
    async def export_template(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @export.sub_command(name="clan", description="Export info for members in a clan")
    async def export_clan(self, ctx: disnake.ApplicationCommandInteraction):
        pass


