import disnake
import calendar
import coc

from utils.clash import heros, heroPets
from disnake.ext import commands
from typing import TYPE_CHECKING, List
from utils.search import search_results
from CustomClasses.CustomPlayer import MyCustomPlayer
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import *
if TYPE_CHECKING:
    from BoardCommands.BoardCog import BoardCog
    cog_class = BoardCog
else:
    cog_class = commands.Cog

class PlayerButtons(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot