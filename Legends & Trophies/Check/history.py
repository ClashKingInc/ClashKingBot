import coc
from disnake.ext import commands
import disnake
import calendar
from CustomClasses.CustomBot import CustomClient
from coc import utils
import re

class History(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def player_convertor(self, player_tag: str):
        player = await self.bot.getPlayer(player_tag=player_tag, raise_exceptions=True)
        return player

    @commands.slash_command(name="history", description="View a players historical legends data")
    async def history_co(self, ctx: disnake.ApplicationCommandInteraction, player: coc.Player = commands.Param(converter=player_convertor)):
      """
        Parameters
        ----------
        player_tag: Player to search for
      """

      embed = disnake.Embed(
            description="Fetching legends history...",
            color=disnake.Color.green())
      await ctx.send(embed=embed)
      embed= await self.create_history(player.tag)
      await ctx.edit_original_message(embed=embed)

    async def create_history(self, tag):
        dates = await self.bot.coc_client.get_seasons(league_id=29000022)
        stats = []
        player = await self.bot.getPlayer(tag)
        if player is None:
            embed = disnake.Embed(description="Not a valid player tag",
                                  color=disnake.Color.red())
            return embed

        results = await self.bot.history_db.find({"tag": tag}).sort("season", -1).to_list(length=None)
        if results is None:
            embed = disnake.Embed(description=f"{player.name} has never finished a season in legends",
                                  color=disnake.Color.red())
            return embed

        names = set()
        for result in results:
            names.add(result.get("name"))
        names = list(names)


        text = ""
        oldyear = "2015"
        embed = disnake.Embed(title=f"**{player.name}'s Legends History**", description="🏆= trophies, 🌎= global rank",color=disnake.Color.from_rgb(r=43, g=45, b=49))
        if names != []:
          names = ", ".join(names)
          embed.add_field(name = "**Previous Names**", value=names, inline=False)
        for result in results:
            season = result.get("season")
            year = season.split("-")[0]
            month = season.split("-")[-1]
            month = calendar.month_name[int(month)]
            month = month.ljust(9)
            month = f"`{month}`"

            year = year[0:4]
            rank = result.get("rank")
            trophies = result.get("trophies")
            if year != oldyear:
              if text != "":
                embed.add_field(name = f"**{oldyear}**", value=text, inline=False)
              oldyear = year
              text = ""
            text += f"{month} | 🏆{trophies} | 🌎{rank}\n"

        if text != "":
            embed.add_field(name = f"**{oldyear}**", value=text, inline=False)

        embed.set_footer(text="Tip: `/check` commands have legends history as well")
        return embed

    @history_co.autocomplete("player")
    async def history_auto_complete(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = set()
        # if search is a player tag, pull stats of the player tag
        if utils.is_valid_tag(query) is True:
            query = utils.correct_tag(tag=query)
            query = query.lower()
            query = re.escape(query)
            results = self.bot.player_stats.find({"$and": [
                {"tag": {"$regex": f"^(?i).*{query}.*$"}}
            ]}).limit(25)
            async for document in results.to_list(length=None):
                name = document.get("name")
                names.add(name + " | " + document.get("tag"))
            return list(names)[:25]

        # ignore capitalization
        # results 3 or larger check for partial match
        # results 2 or shorter must be exact
        # await ongoing_stats.create_index([("name", "text")])

        query = query.lower()
        query = re.escape(query)
        results = self.bot.player_stats.find({"$and": [
            {"name": {"$regex": f"^(?i).*{query}.*$"}}
        ]}).limit(25)
        for document in await results.to_list(length=None):
            names.add(document.get("name") + " | " + document.get("tag"))
        return list(names)[:25]


