from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from Exceptions.CustomExceptions import InvalidGuildID, MessageException
from utils.constants import TOWNHALL_LEVELS
import calendar
import coc
import re

class Convert(commands.Cog, name="Convert"):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def season(self, season: str):
        if season is not None:
            month = list(calendar.month_name).index(season.split(" ")[0])
            year = season.split(" ")[1]
            end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f"0{month}"
            season_date = f"{end_date.year}-{month}"
        else:
            season_date = self.bot.gen_season_date()
        return season_date

    async def server(self, server: str):
        try:
            guild = (await self.bot.getch_guild(int(server.split("|")[-1])))
        except:
            guild = None
        if guild is None:
            raise InvalidGuildID
        return guild


    async def townhall(self, th: str):
        if th is not None:
            ths = th.split(",")
            return [int(th) for th in ths]
        else:
            return list(reversed(TOWNHALL_LEVELS))


    async def clan(self, clan: str):
        clan = await self.bot.getClan(clan_tag=clan, raise_exceptions=True)
        if clan is None:
            return coc.errors.NotFound
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan



    async def player(self, player_tags: str):
        player_tags = player_tags.split(",")[:50]
        players = []
        for player_tag in player_tags:
            player = await self.bot.getPlayer(player_tag=player_tag, custom=True)
            if player is not None:
                players.append(player)
        if not players:
            raise coc.errors.NotFound
        return players


    def hex_code(self, hex_code: str):
        match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)
        if match:
            return hex_code
        raise MessageException(f"{hex_code} is not a valid hex color.")



def setup(bot: CustomClient):
    bot.add_cog(Convert(bot))