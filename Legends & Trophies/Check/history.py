from disnake.ext import commands
import disnake
import calendar
from CustomClasses.CustomBot import CustomClient


class History(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="history", description="View a players historical legends data")
    async def history_co(self, ctx: disnake.ApplicationCommandInteraction, player_tag : str):
      """
        Parameters
        ----------
        player_tag: Player to search for
      """

      embed = disnake.Embed(
            description="Fetching legends history...",
            color=disnake.Color.green())
      await ctx.send(embed=embed)
      embed= await self.create_history(player_tag)
      await ctx.edit_original_message(embed=embed)

    async def create_history(self, tag):
        dates = await self.bot.coc_client.get_seasons(league_id=29000022)
        stats = []
        names = []
        player = await self.bot.getPlayer(tag)
        if player is None:
            embed = disnake.Embed(description="Not a valid player tag",
                                  color=disnake.Color.red())
            return embed

        no_results = True
        for date in dates:
            season_stats = self.bot.history_db[f"{date}"]
            result = await season_stats.find_one({"tag": player.tag})
            if result is not None:
                no_results = False
                stats.append(str(result.get("rank")))
                stats.append(str(result.get("trophies")))
                name = result.get("name")
                #if (name != player.name) and (name not in names):
                  #names.append(name)
            else:
                stats.append("None")
                stats.append("None")

        if no_results:
          embed = disnake.Embed(description=f"{player.name} has never finished a season in legends",
                                  color=disnake.Color.red())
          return embed


        text = ""
        oldyear = "2015"
        embed = disnake.Embed(title=f"**{player.name}'s Legends History**", description="🏆= trophies, 🌎= global rank",color=disnake.Color.blue())
        if names != []:
          names = ", ".join(names)
          #embed.add_field(name = "**Previous Names**", value=names, inline=False)
        for x in range(0, len(stats),2):
            year = dates[int(x/2)]
            month = year[5:]
            month = calendar.month_name[int(month)]
            month = month.ljust(9)
            month = f"`{month}`"

            year = year[0:4]
            rank = stats[x]
            trophies = stats[x+1]
            if rank == "None":
              continue
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


