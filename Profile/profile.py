from disnake.ext import commands
import disnake
from utils.clash import coc_client
from Dictionaries.emojiDictionary import emojiDictionary
from Profile.pagination import button_pagination
from utils.search import search_results


class profiles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="lookup", description="Lookup players or discord users")
    async def lookup(self, ctx: disnake.ApplicationCommandInteraction, tag: str=None, discord_user:disnake.Member=None):
        """
            Parameters
            ----------
            tag: (optional) tag to lookup
            discord_user: (optional) discord user to lookup
        """
        search_query = None
        if tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif tag != None:
            search_query = tag
        else:
            search_query = str(discord_user.id)

        await ctx.response.defer()
        results = await search_results(ctx, search_query)

        if results == []:
            return await ctx.edit_original_message(content="No results were found.", embed=None)


        msg = await ctx.original_message()

        await button_pagination(self.bot, ctx, msg, results)



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