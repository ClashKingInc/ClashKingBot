from discord.ext import commands
import discord




class profiles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="profile", aliases=["lookup", "accounts"])
    async def profile(self, ctx, *, search_query = None):
        if search_query == None:
            search_query = str(ctx.author.id)
        embed = discord.Embed(
            description="<a:loading:884400064313819146> Fetching player profile.",
            color=discord.Color.green())
        msg = await ctx.reply(embed=embed, mention_author=False)

        search = self.bot.get_cog("search")
        results = await search.search_results(ctx, search_query)


        if results == []:
            return await msg.edit(content="No results were found.", embed=None)

        pagination = self.bot.get_cog("pagination")

        await pagination.button_pagination(ctx, msg, results)

        '''
        emoji = emojiDictionary(player.town_hall)

        emoji = emoji.split(":", 2)
        emoji = emoji[2]
        emoji = emoji[0:len(emoji) - 1]
        emoji = self.bot.get_emoji(int(emoji))
        emoji = discord.PartialEmoji(name=emoji.name, id=emoji.id)
        '''





def setup(bot: commands.Bot):
    bot.add_cog(profiles(bot))