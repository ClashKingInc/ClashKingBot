from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utils.ClanCapital import gen_raid_weekend_datestrings
from utils.general import create_superscript
import disnake
import coc
import pytz


class Autocomplete(commands.Cog, name="Autocomplete"):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def season(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if user_input.lower() in season.lower()]


    async def clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        guild_id = ctx.guild.id
        if ctx.filled_options.get("family") is not None:
            if len(ctx.filled_options.get("family").split("|")) == 2:
                guild_id = int(ctx.filled_options.get("family").split("|")[-1])

        clan_list = []
        if query == "":
            pipeline = [
                {"$match" : {"server" : guild_id}},
                {"$sort" : {"name" : 1}},
                {"$limit": 25}]
        else:
            pipeline = [
                {
                    "$search": {
                        "index": "clan_name",
                        "autocomplete": {
                            "query": query,
                            "path": "name",
                        },
                    }
                },
                {"$match": {"server": guild_id}}
            ]
        results = await self.bot.clan_db.aggregate(pipeline=pipeline).to_list(length=None)
        for document in results:
            clan_list.append(f'{document.get("name")} | {document.get("tag")}')

        if clan_list == [] and len(query) >= 3:
            if coc.utils.is_valid_tag(query):
                clan = await self.bot.getClan(query)
            else:
                clan = None
            if clan is None:
                results = await self.bot.coc_client.search_clans(name=query, limit=10)
                for clan in results:
                    league = str(clan.war_league).replace("League ", "")
                    clan_list.append(
                        f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
            else:
                clan_list.append(f"{clan.name} | {clan.tag}")
                return clan_list
        return clan_list[:25]


    async def family_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names


    async def server(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        matches = []
        for guild in self.bot.guilds:
            if guild.member_count < 250:
                continue
            if query.lower() in guild.name.lower():
                matches.append(f"{guild.name} | {guild.id}")
            if len(matches) == 25:
                break
        return matches


    async def timezone(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        all_tz = pytz.common_timezones
        return_list = []
        for tz in all_tz:
            if query.lower() in tz.lower():
                return_list.append(tz)
        return return_list[:25]


    async def raid_weekend(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        weekends = gen_raid_weekend_datestrings(number_of_weeks=25)
        matches = []
        for weekend in weekends:
            if query.lower() in weekend.lower():
                matches.append(weekend)
        return matches



def setup(bot: CustomClient):
    bot.add_cog(Autocomplete(bot))