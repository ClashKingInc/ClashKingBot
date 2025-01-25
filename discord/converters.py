import calendar
import re

import coc
from disnake.ext import commands

from classes.bot import CustomClient
from exceptions.CustomExceptions import InvalidGuildID, MessageException
from utility.constants import TOWNHALL_LEVELS


class Convert(commands.Cog, name='Convert'):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def season(self, season: str):
        if season is not None:
            month = list(calendar.month_name).index(season.split(' ')[0])
            year = season.split(' ')[1]
            end_date = coc.utils.get_season_end(month=int(month - 1), year=int(year))
            month = end_date.month
            if month <= 9:
                month = f'0{month}'
            season_date = f'{end_date.year}-{month}'
        else:
            season_date = self.bot.gen_season_date()
        return season_date

    async def server(self, server: str):
        try:
            guild = await self.bot.getch_guild(int(server.split('|')[-1]), raise_exception=True)
        except:
            guild = await self.bot.getch_guild(923764211845312533)
            guild.__setattr__('id', int(server.split('|')[-1]))
            guild.__setattr__('name', server.split('|')[0])
        if guild is None:
            raise InvalidGuildID
        return guild

    async def townhall(self, th: str):
        if th is not None:
            ths = th.split(',')
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

    async def clan_no_errors(self, clan_tag: str):
        if '|' in clan_tag:
            search = clan_tag.split('|')
            try:
                clan_tag = search[4]
            except Exception:
                clan_tag = search[1]

        clan = await self.bot.coc_client.get_clan(tag=clan_tag)
        return clan

    async def multi_clan(self, clans: str):
        clans = clans.split(',')
        new_clan_list = []
        for clan in clans:
            if '|' in clan:
                splitter = clan.split('|')
                new_clan_list.append(splitter[-1])
            else:
                new_clan_list.append(clan)
        new_clan_list = [coc.utils.correct_tag(t) for t in new_clan_list]
        return new_clan_list

    async def players(self, player_tags: str):
        player_tags = player_tags.split(',')[:50]
        players = []
        for player_tag in player_tags:
            player = await self.bot.getPlayer(player_tag=player_tag, custom=True)
            if player is not None:
                players.append(player)
        if not players:
            raise coc.errors.NotFound
        return players

    async def player(self, player_tag: str):
        player = await self.bot.getPlayer(player_tag=player_tag, custom=False, raise_exceptions=True)
        return player

    async def custom_player(self, player_tag: str):
        player = await self.bot.getPlayer(player_tag=player_tag, custom=True, raise_exceptions=True)
        return player

    async def multi_player(self, player_tags: str):
        player_tags = player_tags.split(',')[:50]
        players = await self.bot.get_players(tags=player_tags, use_cache=True, custom=False)
        if not players:
            raise coc.errors.NotFound
        return players

    def hex_code(self, hex_code: str):
        match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)
        if match:
            return hex_code
        raise MessageException(f'{hex_code} is not a valid hex color.')

    def basic_bool(self, statement: str):
        if statement in ['Yes', 'True', 'Add', "On", "Open"]:
            return True
        return False

    async def ticket_button(self, text: str) -> tuple[str, str]:
        text = text[:-1]
        split_text = text.split('(')
        button_name = split_text[0].strip()
        panel_name = split_text[1].strip()
        return (button_name, panel_name)


def setup(bot: CustomClient):
    bot.add_cog(Convert(bot))
