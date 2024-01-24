from disnake.ext import commands
from classes.bot import CustomClient
from utility.clash.capital import gen_raid_weekend_datestrings
from utility.search import family_names, search_name_with_tag, all_names
from utility.general import create_superscript
from utility.constants import TH_FILTER_OPTIONS, TOWNHALL_LEVELS
import disnake
import coc
import pytz
import re

class Autocomplete(commands.Cog, name="Autocomplete"):
    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def season(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        seasons = self.bot.gen_season_date(seasons_ago=12)[0:]
        return [season for season in seasons if query.lower() in season.lower()]


    async def category(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        categories = []
        for tClan in await tracked.to_list(length=limit):
            category = tClan.get("category")
            if query.lower() in category.lower() and category not in categories:
                categories.append(category)
        return categories[:25]


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


    async def multi_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        guild_id = ctx.guild.id
        if ctx.filled_options.get("family") is not None:
            if len(ctx.filled_options.get("family").split("|")) == 2:
                guild_id = int(ctx.filled_options.get("family").split("|")[-1])

        previous_query = ""
        old_query = query
        if len(query.split(",")) >= 2:
            previous_query = ",".join(query.split(",")[:-1]) + ","
            query = query.split(",")[-1]
            if query == " ":
                query = ""
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
            previous_split = old_query.split(",")[:-1]
            previous_split = [item.strip() for item in previous_split]
            if f'{document.get("name")} | {document.get("tag")}' in previous_split:
                continue
            clan_list.append(f'{previous_query}{document.get("name")} | {document.get("tag")}')
        return clan_list[:25]


    async def family_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await family_names(bot=self.bot, query=query, guild=ctx.guild)
        return names


    async def all_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await all_names(bot=self.bot, query=query)
        return names


    async def banned_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        query = re.escape(query)
        if query == "":
            names = await self.bot.banlist.find({"server" : ctx.guild_id}, limit=25).to_list(length=25)
        else:
            names = await self.bot.banlist.find({"$and": [
                {"server" : ctx.guild_id},
                {"name": {"$regex": f"^(?i).*{query}.*$"}}
            ]}, limit=25).to_list(length=25)
        return [f'{n.get("name")} | {n.get("VillageTag")}' for n in names]


    async def legend_players(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        query = re.escape(query)
        results = await search_name_with_tag(bot=self.bot, poster=False, query=query)
        legend_profile = await self.bot.legend_profile.find_one({'discord_id': ctx.author.id})
        if legend_profile:
            profile_tags = legend_profile.get("profile_tags", [])
            documents = await self.bot.player_stats.find({"$and" : [{"tag" : {"$in": profile_tags}}, {"league" : "Legend League"}]}, {"tag" : 1, "name" : 1, "townhall" : 1}).to_list(length=None)
            results = [(f'‡{create_superscript(document.get("townhall", 0))}{document.get("name")} (Legend)' + " | " + document.get("tag"))
                       for document in documents if query.lower() in document.get("name").lower()] + results
        return results[:25]


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


    async def ticket_panel(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.tickets.distinct("name", filter={"server_id": ctx.guild.id})
        alias_list = []
        for alias in aliases:
            if query.lower() in alias.lower():
                alias_list.append(f"{alias}")
        return alias_list[:25]


    async def multi_ticket_panel(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        aliases = await self.bot.tickets.distinct("name", filter={"server_id": ctx.guild.id})
        alias_list = []
        for alias in ["All Panels"] + aliases:
            if query.lower() in alias.lower():
                alias_list.append(f"{alias}")
        return alias_list[:25]



    async def new_categories(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        categories = await self.bot.clan_db.distinct("category", filter={"server": ctx.guild.id})
        starter_categories = ["General", "Feeder", "War", "Esports"]
        if query != "":
            starter_categories.insert(0, query)
        categories = starter_categories + [c for c in categories if c not in starter_categories]
        return categories[:25]


    async def th_filters(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        always = ["Equal Th Only"] + [str(t) for t in TOWNHALL_LEVELS] + TH_FILTER_OPTIONS
        if query != "":
            always = [a for a in always if query.lower() in a.lower()]
        return always[:25]


def setup(bot: CustomClient):
    bot.add_cog(Autocomplete(bot))