import coc
import disnake
import emoji
import math

from classes.bot import CustomClient
from classes.player.stats import StatsPlayer
from discord import options
from disnake.ext import commands
from exceptions.CustomExceptions import MessageException
from utility.components import create_components, leaderboard_components
from utility.discord_utils import interaction_handler
from .utils import image_board


class Leaderboards(commands.Cog, name="Leaderboards"):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="leaderboard")
    async def leaderboard(self, ctx):
        pass

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
                embed = disnake.Embed(
                    title=f"**{ctx.guild} Legend Leaderboard**", description=text
                )
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                x = 0
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(
                title=f"**{ctx.guild} Legend Leaderboard**", description=text
            )
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)
        return embeds

    @leaderboard.sub_command(name="clans", description="Clan leaderboard of a location")
    async def clan_leaderboards(
        self, ctx: disnake.ApplicationCommandInteraction, country: str
    ):
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
            is_country = country != "International"
            country = coc.utils.get(locations, name=country, is_country=is_country)
            country_names = country.name
            rankings = await self.bot.coc_client.get_location_clans(
                location_id=country.id
            )
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
                embed = disnake.Embed(
                    title=f"{country_names} Top 200 Leaderboard",
                    description=text,
                    color=disnake.Color.green(),
                )
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(
                title=f"{country_names} Top 200 Leaderboard",
                description=text,
                color=disnake.Color.green(),
            )
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        current_page = 0
        await ctx.send(
            embed=embeds[0], components=create_components(current_page, embeds, True)
        )
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check, timeout=600
                )
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)

    @leaderboard.sub_command(
        name="capital", description="Clan Capital leaderboard of a location"
    )
    async def capital_leaderboards(
        self, ctx: disnake.ApplicationCommandInteraction, country: str
    ):
        """
        Parameters
        ----------
        country: country to fetch leaderboard for
        """
        tags = await self.bot.clan_db.distinct("tag", filter={"server": ctx.guild.id})

        if country != "Global":
            locations = await self.bot.coc_client.search_locations(limit=None)
            is_country = country != "International"
            country = coc.utils.get(locations, name=country, is_country=is_country)
            country_names = country.name
            rankings = await self.bot.coc_client.get_location_clans_capital(
                location_id=country.id
            )
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
                embed = disnake.Embed(
                    title=f"{country_names} Top 200 Capital Leaderboard",
                    description=text,
                    color=disnake.Color.green(),
                )
                if ctx.guild.icon is not None:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(
                title=f"{country_names} Top 200 Capital Leaderboard",
                description=text,
                color=disnake.Color.green(),
            )
            if ctx.guild.icon is not None:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            embeds.append(embed)

        current_page = 0
        await ctx.send(
            embed=embeds[0], components=create_components(current_page, embeds, True)
        )
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check, timeout=600
                )
            except:
                await msg.edit(components=[])
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.send(embed=embed)

    @leaderboard.sub_command(
        name="players", description="Player leaderboard of a location"
    )
    async def player_leaderboards(
        self, ctx: disnake.ApplicationCommandInteraction, country: str, limit=100
    ):
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
                return await ctx.edit_original_message(
                    content="Not a valid country, choose one of the 100+ options from the autocomplete."
                )
            locations = await self.bot.coc_client.search_locations(limit=None)
            country = coc.utils.get(locations, name=country, is_country=True)
            embeds = await self.create_country_lb(country.id, ctx)

        current_page = 0
        await ctx.edit_original_message(
            embed=embeds[0], components=create_components(current_page, embeds, True)
        )
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction", check=check, timeout=600
                )
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.response.edit_message(
                    embed=embeds[current_page],
                    components=create_components(current_page, embeds, True),
                )

            elif res.data.custom_id == "Print":
                await msg.delete()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)

    async def create_country_lb(self, location_id):

        if location_id == "global":
            country = await self.bot.coc_client.get_location_players(
                location_id="global"
            )
            country_name = "Global"
        else:
            location_id = int(location_id)
            country = await self.bot.coc_client.get_location_players(
                location_id=location_id
            )
            country_name = await self.bot.coc_client.get_location(location_id)

        x = 1
        text = ""
        embeds = []
        y = 0
        member_tags = [member.tag for member in country]
        players = await self.bot.get_players(tags=member_tags)
        players = sorted(players, key=lambda x: x.trophies, reverse=True)
        for player in players:
            player: StatsPlayer
            rank = str(x) + "."
            rank = rank.ljust(3)
            x += 1
            name = emoji.get_emoji_regexp().sub("", player.name)
            hit_text = " "
            if player.results is not None:
                legend_day = player.legend_day()
                hit_text = f"\n` ➼ ` <:sword:825589136026501160> {legend_day.attack_sum}{legend_day.num_attacks.superscript} <:clash:877681427129458739> {legend_day.defense_sum}{legend_day.num_defenses.superscript}"

            text += f"`{rank}`\u200e**<:trophyy:849144172698402817>\u200e{player.trophies} | \u200e{name}**{hit_text}\n"
            y += 1
            if y == 30:
                embed = disnake.Embed(
                    title=f"**{country_name} Legend Leaderboard**", description=text
                )
                y = 0
                embeds.append(embed)
                text = ""

        if text != "":
            embed = disnake.Embed(
                title=f"**{country_name} Legend Leaderboard**", description=text
            )
            embeds.append(embed)

        if text == "" and embeds == []:
            embed = disnake.Embed(
                title=f"**{country_name} Legend Leaderboard**",
                description="No Legend Players in Region",
            )
            embeds.append(embed)

        return embeds


def setup(bot: CustomClient):
    bot.add_cog(Leaderboards(bot))
