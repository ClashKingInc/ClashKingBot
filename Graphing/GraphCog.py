from disnake.ext import commands
from .Graphs import GraphCreator
from .DWGraphs import DataWrapperGraphs
from .GraphUtils import GraphUtils

class GraphCog(GraphCreator, DataWrapperGraphs, GraphUtils, commands.Cog, name="Graphing"):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

def setup(bot):
    bot.add_cog(GraphCog(bot))