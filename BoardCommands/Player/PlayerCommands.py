import disnake
import calendar
import coc

from utils.troop_methods import heros, heroPets
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

class PlayerCommands(commands.Cog):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def season_convertor(self, season: str):
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

    @commands.slash_command(name="player")
    async def player(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user": ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        await ctx.response.defer(ephemeral=ephemeral)

    @player.sub_command(name="donations", description="Donations for all of a player's accounts")
    async def donations(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None,
                        season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        if discord_user is None:
            discord_user = ctx.author
        players: List[MyCustomPlayer] = await search_results(self.bot, str(discord_user.id))
        if not players:
            raise NoLinkedAccounts

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        footer_icon = discord_user.display_avatar.url
        embed: disnake.Embed = await board_cog.donation_board(players=players, season=season, footer_icon=footer_icon, title_name=f"{discord_user.display_name}", type="donations")
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"donatedplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Received", emoji=self.bot.emoji.clan_castle.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"receivedplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Ratio", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"ratioplayer_{season}_{discord_user.id}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])

    @player.sub_command(name="capital", description="Capital stats for a player or a user's accounts")
    async def capital(self, ctx: disnake.ApplicationCommandInteraction, player_tag: str= None, discord_user: disnake.Member = None):
        pass



    @player.sub_command(name="search", description="Search for players")
    async def search(self, ctx: disnake.ApplicationCommandInteraction, clan:str = commands.Param(choices=["No Clan", "In Clan"], default=None),
                     league: str = commands.Param(choices=["No League", "Has League"], default=None),
                     townhall: int = commands.Param(default=None, gt=8), trophies: int = None, war_stars:int = None, clan_capital_donos: int = None, attacks: int = None):
        msg = await ctx.original_message()
        while True:
            embed, buttons = await self.create_search(clan=clan, townhall=townhall, trophies=trophies, war_stars=war_stars, clan_capital_donos=clan_capital_donos,
                                                      league=league, attacks=attacks)
            await ctx.edit_original_message(embed=embed, components=buttons)
            try:
                res = await interaction_handler(bot=self.bot, ctx=ctx)
            except:
                await msg.edit(components=[])


    async def create_search(self, clan, townhall, trophies, war_stars, clan_capital_donos, league, attacks):
        queries = {}
        queries['$and'] = []
        if clan == "No Clan":
            queries['$and'].append({'data.clan.tag': {"$eq": None}})
        elif clan == "In Clan":
            queries['$and'].append({'data.clan.tag': {"$ne": None}})

        if league == "No League":
            queries['$and'].append({'data.league.name': {"$eq": None}})
        elif league == "Has League":
            queries['$and'].append({'data.league.name': {"$ne": None}})

        if townhall is not None:
            queries['$and'].append({"data.townHallLevel" : int(townhall)})

        if trophies is not None:
            queries['$and'].append({"data.trophies" : {"$gte": int(trophies)}})

        if attacks is not None:
            queries['$and'].append({"data.attackWins" : {"$gte": int(attacks)}})

        if war_stars is not None:
            queries['$and'].append({"data.warStars" : {"$gte": int(war_stars)}})

        if clan_capital_donos is not None:
            queries['$and'].append({"data.clanCapitalContributions" : {"$gte": int(clan_capital_donos)}})

        if queries["$and"] == []:
            queries = {}

        player = []
        tries = 0
        while player == []:
            pipeline = [{"$match": queries}, {"$sample": {"size": 3}}]
            player_list = await self.bot.player_cache.aggregate(pipeline).to_list(length=3)
            if player_list == [] or tries == 3:
                return disnake.Embed(description="**No Results Found**", color=disnake.Color.red()), []
            players = await self.bot.get_players(tags=[player.get("tag") for player in player_list], custom=True, use_cache=False)
            player = [player for player in players if player.results is not None]
            if player == []:
                tries += 1
        player = player[:1][0]
        #players = [MyCustomPlayer(data=data.get("data"), client=self.bot.coc_client, bot=self.bot, results=None) for data in player_list]
        player_links = await self.bot.link_client.get_links(*[player.tag])
        player_link_dict = dict(player_links)

        hero = heros(bot=self.bot, player=player)
        pets = heroPets(bot=self.bot, player=player)
        if hero is None:
            hero = ""
        else:
            hero = f"**Heroes:**\n{hero}\n"

        if pets is None:
            pets = ""
        else:
            pets = f"**Pets:**\n{pets}\n"

        if player.last_online is not None:
            lo = f"<t:{player.last_online}:R>"
        else:
            lo = "`N/A`"

        discord = self.bot.emoji.green_status if player_link_dict.get(player.tag) is not None else self.bot.emoji.red_status

        embed = disnake.Embed(title=f"**Invite {player.name} to your clan:**",
                              description=f"{player.town_hall_cls.emoji}{player.name} - TH{player.town_hall}\n" +
                                          f"{self.bot.emoji.hashmark}Tag: {player.tag}\n" +
                                          f"{self.bot.emoji.clan_castle}Clan: {player.clan_name()}\n" +
                                          f"{self.bot.emoji.trophy}Trophies: {player.trophies} | Attacks: {player.attack_wins}\n"
                                          f"{self.bot.emoji.war_star}War Stars: {player.war_stars}\n"
                                          f"{self.bot.emoji.capital_gold}Capital Donos: {player.clan_capital_contributions}\n"
                                          f"{self.bot.emoji.clock}{lo} {self.bot.emoji.discord}{discord}\n"
                                          f"{hero}{pets}",
                              color=disnake.Color.green())
        if str(player.league) != "Unranked":
            embed.set_thumbnail(url=player.league.icon.url)
        else:
            embed.set_thumbnail(url=self.bot.emoji.unranked.partial_emoji.url)

        stat_buttons = [
            disnake.ui.Button(label=f"Open In-Game",
                              url=player.share_link),
            disnake.ui.Button(label=f"Clash of Stats",
                              url=f"https://www.clashofstats.com/players/{player.tag.strip('#')}/summary"),
            disnake.ui.Button(label=f"Next", emoji=self.bot.emoji.right_green_arrow.partial_emoji, custom_id="NextSearch")]
        buttons = disnake.ui.ActionRow()
        for button in stat_buttons:
            buttons.append_item(button)

        return embed, [buttons]







    @player.sub_command(name="activity", description="Activity stats for all of a player's accounts")
    async def activity(self, ctx: disnake.ApplicationCommandInteraction, discord_user: disnake.Member = None,
                       season: str = commands.Param(default=None, convert_defaults=True, converter=season_convertor)):
        if discord_user is None:
            discord_user = ctx.author
        players: List[MyCustomPlayer] = await search_results(self.bot, str(discord_user.id))
        if not players:
            raise NoLinkedAccounts

        board_cog: BoardCog = self.bot.get_cog("BoardCog")
        footer_icon = discord_user.display_avatar.url
        embed: disnake.Embed = await board_cog.activity_board(players=players, season=season, footer_icon=footer_icon,title_name=f"{discord_user.display_name}")

        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"activityplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Last Online", emoji=self.bot.emoji.clock.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"lastonlineplayer_{season}_{discord_user.id}"))
        buttons.append_item(disnake.ui.Button(
            label="Graph", emoji=self.bot.emoji.ratio.partial_emoji,
            style=disnake.ButtonStyle.grey, custom_id=f"activitygraphplayer_{season}_{discord_user.id}"))

        await ctx.edit_original_message(embed=embed, components=[buttons])


    @donations.autocomplete("season")
    @activity.autocomplete("season")
    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]