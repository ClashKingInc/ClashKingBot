import coc
import disnake
from Exceptions.CustomExceptions import MessageException
from utils.clash import gen_season_date
from CustomClasses.CustomPlayer import MyCustomPlayer
from utils.constants import SHORT_PLAYER_LINK

class StatsClan():
    def __init__(self, bot, data: dict, clan: coc.Clan):
        self.data = data
        self.clan = clan
        self.bot = bot

    async def get_season(self, season: str = None):
        if season is None:
            season = gen_season_date()
        season_data = self.data.get(season, {})

        member_tags = list(season_data.keys())
        other_data = {}
        if season == gen_season_date():
            member_tags += [member.tag for member in self.clan.members]
            other_data = {member.tag : {} for member in self.clan.members}
        season_players = await self.bot.get_players(custom=False, tags=member_tags, use_cache=True)
        season_players = {p.tag : p._raw_data for p in season_players}
        other_data |= season_data

        #print(season_players)

        for tag, member_tags in season_data.items():
            if season_players.get(tag) is None:
                print(tag)

        return Season(data=season_data, player_data=season_players, bot=self.bot)


class Season():
    def __init__(self, data: dict, player_data: dict, bot):
        self.data = data
        self.members = [SeasonMembers(bot=bot, tag=tag, data=member_data, p_data=player_data.get(tag, {})) for tag, member_data in self.data.items()]


class SeasonMembers():
    def __init__(self, bot, tag: str, data: dict, p_data:dict):
        self.tag = tag
        self.player = MyCustomPlayer(data=p_data, client=bot.coc_client, bot=bot, results={})
        self.activity = data.get("activity", 0)
        self.donated = data.get("donated", 0)
        self.received = data.get("received", 0)
        self.attack_wins = data.get("attack_wins", 0)
        self.gold_looted = data.get("gold_looted", 0)
        self.elixir_looted = data.get("elixir_looted", 0)
        self.dark_elixir_looted = data.get("dark_elixir_looted", 0)
        self.clan_games = data.get("clan_games", 0)
        self.share_link = f"{SHORT_PLAYER_LINK}{self.tag.strip('#')}"

    @property
    def dono_ratio(self):
        donations = self.donated
        received = self.received
        if received == 0:
            received = 1
        if int(donations / received) >= 1000:
            return int(donations / received)
        elif int(donations / received) >= 100:
            round(donations / received, 1)
        return round(donations / received, 2)

class BanEntry():
    def __init__(self, data: dict):
        self.data = data
        self.player_tag = data.get("VillageTag")
        self.player_name = data.get("VillageName")

    @property
    def date_created(self):
        date = self.data.get("DateCreated")


