from disnake.ext import commands
import disnake
import coc
from utils.components import create_components
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomPlayer import MyCustomPlayer
from utils.components import leaderboard_components
from BoardCommands.Utils import Shared as shared_embeds
from Exceptions.CustomExceptions import MessageException
from utils.discord_utils import interaction_handler

import math
import emoji

class Leaderboards(commands.Cog, name="Leaderboards"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="leaderboard")
    async def leaderboard(self, ctx):
        pass

    @leaderboard.sub_command(name="family", description="Server's player trophy leaderboard")
    async def top(self, ctx: disnake.ApplicationCommandInteraction, limit: int = 100):
        """
            Parameters
            ----------
            limit: number of players to show
        """
        await ctx.response.defer()
        rankings = []
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        l = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=l):
            tag = clan.get("tag")
            clan = await self.bot.getClan(tag)
            if clan is None:
                continue
            for player in clan.members:
                try:
                    playerStats = []
                    playerStats.append(player.name)
                    playerStats.append(player.trophies)
                    playerStats.append(player.clan.name)
                    playerStats.append(player.tag)
                    rankings.append(playerStats)
                except:
                    continue

        if len(rankings) == 0:
            return await ctx.send(content=f"No players to display.")

        if limit < 1:
            return await ctx.send(content=f"Please use a number between 1 - {len(rankings)}.")

        if limit > len(rankings):
            limit = len(rankings)

        ranking = sorted(rankings, key=lambda l: l[1], reverse=True)
        cum_score = 0
        if limit == 50:
            z = 1
            for r in rankings:
                if z >= 1 and z <= 10:
                    cum_score += (ranking[z - 1][1]) * 0.50
                elif z >= 11 and z <= 20:
                    cum_score += (ranking[z - 1][1]) * 0.25
                elif z >= 21 and z <= 30:
                    cum_score += (ranking[z - 1][1]) * 0.12
                elif z >= 31 and z <= 40:
                    cum_score += (ranking[z - 1][1]) * 0.10
                elif z >= 41 and z <= 50:
                    cum_score += (ranking[z - 1][1]) * 0.03
                z += 1

        cum_score = int(cum_score)

        cum_score = "{:,}".format(cum_score)

        embeds = []
        length = math.ceil(limit / 50)
        current_page = 0

        for e in range(0, length):

            rText = ''
            max = limit
            if (e + 1) * 50 < limit:
                max = (e + 1) * 50
            for x in range(e * 50, max):
                # print(ranking[x])
                place = str(x + 1) + "."
                place = place.ljust(3)
                rText += f"\u200e`{place}` \u200e<:trophy:956417881778815016> \u200e{ranking[x][1]} - \u200e{ranking[x][0]} | \u200e{ranking[x][2]}\n"

            embed = disnake.Embed(title=f"**Top {limit} {ctx.guild} players**",
                                  description=rText)
            if limit == 50:
                embed.set_footer(text=f"Cumulative Trophies would be 🏆{cum_score}")
            embeds.append(embed)

        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            # print(res.custom_id)
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)
                return

    @leaderboard.sub_command(name="legends", description="Server's legend players leaderboard")
    async def legend_leaderboard(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

        clan_tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})
        legend_players = await self.bot.player_stats.find({"$and": [{"clan_tag": {"$in": clan_tags}}, {"league": "Legend League"}]}).sort(f"trophies", -1).to_list(length=None)
        if not legend_players:
            raise MessageException("No Players in Family are in Legend League.")
        legend_players = await self.bot.get_players(tags=[p["tag"] for p in legend_players], found_results=legend_players, custom=True)
        legend_players.sort(key=lambda x : x.trophies, reverse=True)
        guild_icon = ctx.guild.icon.url if ctx.guild.icon else self.bot.user.avatar.url

        #chunk into groups of 20
        legend_players_chunked = [legend_players[i * 20:(i + 1) * 20] for i in range((len(legend_players) + 20 - 1) // 20)]


        sort_types = {0: "Alphabetically", 1: "by Start Trophies", 2: "by Offense", 4: "by Defense",
                      6: "by Current Trophies"}
        sort_type = 6
        current_page = 0

        picture = await shared_embeds.image_board(bot=self.bot, players=legend_players_chunked[current_page], logo_url=guild_icon, title=f'{ctx.guild.name} Legend Board', type="legend")

        await ctx.edit_original_message(content=picture, components=leaderboard_components(self.bot, current_page, len(legend_players_chunked)))

        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, any_run=True)

            #check if is the dropdown or buttons, buttons is type 2
            if res.data.component_type.value == 2:
                if res.data.custom_id == "Previous":
                    current_page -= 1
                    picture = await shared_embeds.image_board(bot=self.bot, players=legend_players_chunked[current_page], logo_url=guild_icon,
                                                              title=f'{ctx.guild.name} Legend Board', type="legend", start_number=20 * current_page)
                    await res.edit_original_message(content=picture,
                                                    components=leaderboard_components(self.bot, current_page, len(legend_players_chunked)))

                elif res.data.custom_id == "Next":
                    current_page += 1
                    picture = await shared_embeds.image_board(bot=self.bot, players=legend_players_chunked[current_page], logo_url=guild_icon,
                                                              title=f'{ctx.guild.name} Legend Board', type="legend", start_number=20 * current_page)
                    await res.edit_original_message(content=picture,
                                                    components=leaderboard_components(self.bot, current_page, len(legend_players_chunked)))

            else:
                current_page = 0
                sort_type = int(res.values[0])
                sort_types = {0: "Alphabetically", 1: "by Start Trophies", 2: "by Offense", 4: "by Defense",
                              6: "by Current Trophies"}
                if sort_type == 0:
                    legend_players.sort(key=lambda x: x.name.lower(), reverse=False)
                elif sort_type == 1:
                    legend_players.sort(key=lambda x: x.trophy_start(), reverse=True)
                elif sort_type == 2:
                    legend_players.sort(key=lambda x: x.legend_day().attack_sum, reverse=True)
                elif sort_type == 4:
                    legend_players.sort(key=lambda x: x.legend_day().defense_sum, reverse=True)
                elif sort_type == 6:
                    legend_players.sort(key=lambda x: x.trophies, reverse=True)

                # chunk into groups of 30
                legend_players_chunked = [legend_players[i * 20:(i + 1) * 20] for i in range((len(legend_players) + 20 - 1) // 20)]
                picture = await shared_embeds.image_board(bot=self.bot, players=legend_players_chunked[current_page], logo_url=guild_icon,
                                                          title=f'{ctx.guild.name} Legend Board', type="legend", start_number=20 * current_page)
                await res.edit_original_message(content=picture,
                                                components=leaderboard_components(self.bot, current_page, len(legend_players_chunked)))

    async def create_player_embed(self, ctx, ranking):
        text = ""
        initial = f"__**{ctx.guild.name} Legend Leaderboard**__\n"
        embeds = []
        x = 0
        for player in ranking:
            name = player[0]
            hits = player[2]
            numHits = player[3]
            defs = player[4]
            numDefs = player[5]
            trophies = player[6]
            text += f"\u200e**<:trophyy:849144172698402817>\u200e{trophies} | \u200e{name}**\n➼ <:sword_coc:940713893926428782> {hits}{numHits} <:clash:877681427129458739> {defs}{numDefs}\n"
            x += 1
            if x == 25:
                embed = disnake.Embed(title=f"**{ctx.guild} Legend Leaderboard**",
                                      description=text)
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                x = 0
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"**{ctx.guild} Legend Leaderboard**",
                                  description=text)
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)
        return embeds

    @leaderboard.sub_command(name="clans", description="Clan leaderboard of a location")
    async def clan_leaderboards(self, ctx: disnake.ApplicationCommandInteraction, country: str ):
        """
            Parameters
            ----------
            country: country to fetch leaderboard for
        """
        tags = []
        tracked = self.bot.clan_db.find({"server": ctx.guild.id})
        limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
        for clan in await tracked.to_list(length=limit):
            tag = clan.get("tag")
            tags.append(tag)

        if country != "Global":
            locations = await self.bot.coc_client.search_locations(limit=None)
            is_country = (country != "International")
            country = coc.utils.get(locations, name=country, is_country=is_country)
            country_names = country.name
            rankings = await self.bot.coc_client.get_location_clans(location_id=country.id)
        else:
            rankings = await self.bot.coc_client.get_location_clans()
            country_names = "Global"

        x = 0
        embeds = []
        text = ""
        for clan in rankings:
            rank = str(x + 1)
            rank = rank.ljust(2)
            star = ""
            if clan.tag in tags:
                star = "⭐"
            text += f"`\u200e{rank}`🏆`\u200e{clan.points}` \u200e{clan.name}{star}\n"
            x += 1
            if x != 0 and x % 50 == 0:
                embed = disnake.Embed(title=f"{country_names} Top 200 Leaderboard",
                                      description=text,
                                      color=disnake.Color.green())
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"{country_names} Top 200 Leaderboard",
                                  description=text,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)

    @leaderboard.sub_command(name="capital", description="Clan Capital leaderboard of a location")
    async def capital_leaderboards(self, ctx: disnake.ApplicationCommandInteraction, country: str):
        """
            Parameters
            ----------
            country: country to fetch leaderboard for
        """
        tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})

        if country != "Global":
            locations = await self.bot.coc_client.search_locations(limit=None)
            is_country = (country != "International")
            country = coc.utils.get(locations, name=country, is_country=is_country)
            country_names = country.name
            rankings = await self.bot.coc_client.get_location_clans_capital(location_id=country.id)
        else:
            rankings = await self.bot.coc_client.get_location_clans_capital()
            country_names = "Global"

        x = 0
        embeds = []
        text = ""
        for clan in rankings:
            rank = str(x + 1)
            rank = rank.ljust(2)
            star = ""
            if clan.tag in tags:
                star = "⭐"
            text += f"`\u200e{rank}`<:capital_trophy:1054056202864177232>`\u200e{clan.capital_points}` \u200e{clan.name}{star}\n"
            x += 1
            if x != 0 and x % 50 == 0:
                embed = disnake.Embed(title=f"{country_names} Top 200 Capital Leaderboard",
                                      description=text,
                                      color=disnake.Color.green())
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"{country_names} Top 200 Capital Leaderboard",
                                  description=text,
                                  color=disnake.Color.green())
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        current_page = 0
        await ctx.send(embed=embeds[0], components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)

    @leaderboard.sub_command(name="players", description="Player leaderboard of a location")
    async def player_leaderboards(self, ctx: disnake.ApplicationCommandInteraction, country: str, limit=100):
        """
            Parameters
            ----------
            country: country to fetch leaderboard for
            limit: default 100, set to 25 for a refreshable board
        """
        await ctx.response.defer()
        loc = await self.bot.coc_client.get_location_named(country)
        if country == "Global":
            embeds = await self.create_country_lb("global", ctx)
        else:
            if loc is None:
                return await ctx.edit_original_message(content="Not a valid country, choose one of the 100+ options from the autocomplete.")
            locations = await self.bot.coc_client.search_locations(limit=None)
            country = coc.utils.get(locations, name=country, is_country=True)
            embeds = await self.create_country_lb(country.id, ctx)

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0],components=create_components(current_page, embeds, True))
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    async def create_country_lb(self, location_id, ctx):

        if location_id == "global":
            country = await self.bot.coc_client.get_location_players(location_id="global")
            country_name = "Global"
        else:
            location_id = int(location_id)
            country = await self.bot.coc_client.get_location_players(location_id=location_id)
            country_name = await self.bot.coc_client.get_location(location_id)

        x = 1
        text = ""
        embeds = []
        y = 0
        member_tags = [member.tag for member in country]
        players = await self.bot.get_players(tags=member_tags)
        players = sorted(players, key=lambda x : x.trophies, reverse=True)
        for player in players:
            player: MyCustomPlayer
            rank = str(x) + "."
            rank = rank.ljust(3)
            x +=1
            name = emoji.get_emoji_regexp().sub('', player.name)
            hit_text = " "
            if player.results is not None:
                legend_day = player.legend_day()
                hit_text = f"\n` ➼ ` <:sword:825589136026501160> {legend_day.attack_sum}{legend_day.num_attacks.superscript} <:clash:877681427129458739> {legend_day.defense_sum}{legend_day.num_defenses.superscript}"

            text += f"`{rank}`\u200e**<:trophyy:849144172698402817>\u200e{player.trophies} | \u200e{name}**{hit_text}\n"
            y += 1
            if y == 30:
                embed = disnake.Embed(title=f"**{country_name} Legend Leaderboard**",
                                      description=text)
                y = 0
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(title=f"**{country_name} Legend Leaderboard**",
                                  description=text)
            embeds.append(embed)

        if text == "" and embeds == []:
            embed = disnake.Embed(title=f"**{country_name} Legend Leaderboard**",
                                  description="No Legend Players in Region")
            embeds.append(embed)

        return embeds

    @clan_leaderboards.autocomplete("country")
    @player_leaderboards.autocomplete("country")
    @capital_leaderboards.autocomplete("country")
    async def autocomp_names(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        locations = await self.bot.coc_client.search_locations()
        results = []
        if query.lower() in "Global":
            results.append("Global")
        for location in locations:
            if query.lower() in location.name.lower():
                ignored = ["Africa", "Europe", "North America", "South America", "Asia"]
                if location.name not in ignored:
                    if location.name not in results:
                        results.append(location.name)
        return results[0:25]


def setup(bot: CustomClient):
    bot.add_cog(Leaderboards(bot))