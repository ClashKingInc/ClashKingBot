from disnake.ext import commands
import disnake
from utils.clashClient import coc_client
from Dictionaries.emojiDictionary import emojiDictionary



class profiles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="profile", aliases=["lookup", "accounts"])
    async def profile(self, ctx, *, search_query = None):
        if search_query == None:
            search_query = str(ctx.author.id)
        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Fetching player profile.",
            color=disnake.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        search = self.bot.get_cog("search")
        results = await search.search_results(ctx, search_query)


        if results == []:
            return await msg.edit(content="No results were found.", embed=None)

        pagination = self.bot.get_cog("pagination")

        await pagination.button_pagination(ctx, msg, results)



    @commands.command(name="list")
    async def list(self, ctx, *, search_query=None):
        if search_query == None:
            search_query = str(ctx.author.id)
        embed = disnake.Embed(
            description="<a:loading:884400064313819146> Fetching player profile.",
            color=disnake.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        search = self.bot.get_cog("search")
        results = await search.search_results(ctx, search_query)

        if results == []:
            return await msg.edit(content="No results were found.", embed=None)

        text = ""
        total = 0
        sumth = 0

        async for player in coc_client.get_players(results):
            emoji = emojiDictionary(player.town_hall)
            th = player.town_hall
            sumth += th
            total += 1
            text += f"{emoji} {player.name}\n"

        average = round((sumth / total), 2)
        embed = disnake.Embed(
            description=text,
            color=disnake.Color.green())

        embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
        await msg.edit(embed=embed)







def setup(bot: commands.Bot):
    bot.add_cog(profiles(bot))